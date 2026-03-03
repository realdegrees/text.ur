"""Endpoints for managing document tasks and task responses."""

from uuid import uuid4

from api.dependencies.authentication import Authenticate
from api.dependencies.database import Database
from api.dependencies.events import Events
from api.dependencies.resource import Resource
from core.app_exception import AppException
from fastapi import Body, Request, Response
from models.enums import AnswerType, AppErrorCode, Permission, StringMatchMode
from models.event import Event
from models.tables import (
    Document,
    Task,
    TaskOption,
    TaskResponse,
    User,
)
from models.task import (
    MAX_TASKS_PER_DOCUMENT,
    TaskAdminRead,
    TaskCreate,
    TaskOptionCreate,
    TaskRead,
    TaskReorder,
    TaskResponseCreate,
    TaskResponseRead,
    TasksUpdatedEvent,
    TaskUpdate,
)
from sqlmodel import delete, func, select, update
from util.api_router import APIRouter
from util.cache import invalidate_group_scores, invalidate_user_score
from util.queries import Guard

router = APIRouter(
    prefix="/documents/{document_id}/tasks",
    tags=["Tasks"],
)

# Default epsilon for floating-point equality comparison
_NUMBER_EPSILON = 1e-9


# ========================================================================
# ========================= Helper functions ============================
# ========================================================================


def _is_admin(user: User, document: Document) -> bool:
    """Check whether the user is an admin/owner of the document's group.

    Reuses the same logic as Guard.document_access: owner or
    ADMINISTRATOR permission.
    """
    return any(
        m.user_id == user.id and m.accepted and (m.is_owner or Permission.ADMINISTRATOR in (m.permissions or []))
        for m in document.group.memberships
    )


def check_task_answer(task: Task, answer: dict) -> bool:
    """Determine if the given answer is correct for the task."""
    if task.answer_type == AnswerType.MULTIPLE_CHOICE:
        selected = set(answer.get("selected_option_ids", []))
        correct = {o.id for o in task.options if o.is_correct}
        return selected == correct

    if task.answer_type == AnswerType.STRING:
        text = answer.get("text", "")
        expected = task.correct_string_answer or ""
        if task.string_match_mode == StringMatchMode.EXACT:
            return text == expected
        return text.strip().lower() == expected.strip().lower()

    if task.answer_type == AnswerType.NUMBER:
        value = answer.get("value")
        if value is None or task.correct_number_answer is None:
            return False
        tolerance = task.number_tolerance if task.number_tolerance is not None else _NUMBER_EPSILON
        return abs(float(value) - task.correct_number_answer) <= tolerance

    return False


def _build_correct_answer(task: Task) -> dict:
    """Build the correct-answer dict to reveal to the user."""
    if task.answer_type == AnswerType.MULTIPLE_CHOICE:
        return {
            "selected_option_ids": [o.id for o in task.options if o.is_correct],
        }
    if task.answer_type == AnswerType.STRING:
        return {"text": task.correct_string_answer}
    if task.answer_type == AnswerType.NUMBER:
        result: dict = {"value": task.correct_number_answer}
        if task.number_tolerance is not None:
            result["tolerance"] = task.number_tolerance
        return result
    return {}


async def _replace_options(
    db: Database,
    task: Task,
    options: list[TaskOptionCreate],
) -> None:
    """Delete existing options and create replacements."""
    # Delete old options
    for opt in list(task.options):
        await db.delete(opt)
    await db.flush()

    # Create new options
    for idx, opt_data in enumerate(options):
        opt = TaskOption(
            task_id=task.id,
            label=opt_data.label,
            is_correct=opt_data.is_correct,
            order=opt_data.order if opt_data.order != 0 else idx,
        )
        db.add(opt)


async def _publish_tasks_updated(
    events: Events,
    document_id: str,
    request: Request,
) -> None:
    """Publish a tasks_updated WebSocket event."""
    await events.publish(
        Event[TasksUpdatedEvent](
            event_id=uuid4(),
            type="tasks_updated",
            payload=TasksUpdatedEvent(document_id=document_id),
            resource_id=document_id,
            resource="tasks",
            originating_connection_id=request.headers.get("X-Connection-ID"),
        ).model_dump(mode="json"),
        f"documents:{document_id}:comments",
    )


# ========================================================================
# ========================= Task CRUD (Admin) ===========================
# ========================================================================


@router.post("/", response_model=TaskAdminRead, status_code=201)
async def create_task(
    db: Database,
    events: Events,
    request: Request,
    session_user: User = Authenticate(guards=[Guard.document_access({Permission.ADMINISTRATOR})]),
    task_create: TaskCreate = Body(...),
    document: Document = Resource(Document, param_alias="document_id"),
) -> TaskAdminRead:
    """Create a new task for the document."""
    # Check max tasks limit
    result = await db.exec(select(func.count(Task.id)).where(Task.document_id == document.id))
    task_count = result.one()
    if task_count >= MAX_TASKS_PER_DOCUMENT:
        raise AppException(
            status_code=400,
            error_code=AppErrorCode.VALIDATION_ERROR,
            detail=(f"Document has reached the maximum of {MAX_TASKS_PER_DOCUMENT} tasks."),
        )

    # Compute order server-side to prevent collisions from gaps
    # left by deleted tasks.
    max_order_result = await db.exec(select(func.coalesce(func.max(Task.order), -1)).where(Task.document_id == document.id))
    next_order = max_order_result.one() + 1

    task = Task(
        document_id=document.id,
        question=task_create.question,
        answer_type=task_create.answer_type,
        correct_string_answer=task_create.correct_string_answer,
        correct_number_answer=task_create.correct_number_answer,
        number_tolerance=task_create.number_tolerance,
        string_match_mode=task_create.string_match_mode,
        points=task_create.points,
        order=next_order,
        max_attempts=task_create.max_attempts,
    )
    db.add(task)
    await db.flush()

    # Create options (for MC type)
    for idx, opt_data in enumerate(task_create.options):
        opt = TaskOption(
            task_id=task.id,
            label=opt_data.label,
            is_correct=opt_data.is_correct,
            order=opt_data.order if opt_data.order != 0 else idx,
        )
        db.add(opt)

    await db.commit()
    await db.refresh(task)

    await invalidate_group_scores(document.group_id)
    await _publish_tasks_updated(events, document.id, request)

    return TaskAdminRead.model_validate(task)


@router.get("/")
async def list_tasks(
    db: Database,
    session_user: User = Authenticate(guards=[Guard.document_access()]),
    document: Document = Resource(Document, param_alias="document_id"),
) -> list[TaskAdminRead] | list[TaskRead]:
    """List all tasks for a document (ordered).

    Admins see correct answers; members do not.
    """
    result = await db.exec(select(Task).where(Task.document_id == document.id).order_by(Task.order, Task.id))
    tasks = result.all()

    if _is_admin(session_user, document):
        return [TaskAdminRead.model_validate(t) for t in tasks]
    return [TaskRead.model_validate(t) for t in tasks]


# ========================================================================
# == Fixed route ordering: literal paths BEFORE parameterised paths =====
# ========================================================================


@router.put("/reorder", response_model=list[TaskAdminRead])
async def reorder_tasks(
    db: Database,
    events: Events,
    request: Request,
    session_user: User = Authenticate(guards=[Guard.document_access({Permission.ADMINISTRATOR})]),
    reorder: TaskReorder = Body(...),
    document: Document = Resource(Document, param_alias="document_id"),
) -> list[TaskAdminRead]:
    """Reorder a subset of tasks within a document.

    Accepts a partial list of task IDs in the desired order.
    Only the submitted tasks are reordered — all others keep
    their current positions. The submitted tasks swap into
    each other's order slots.
    """
    result = await db.exec(
        select(Task).where(
            Task.document_id == document.id,
            Task.id.in_(reorder.task_ids),
        )
    )
    tasks_by_id = {t.id: t for t in result.all()}

    # Validate all submitted IDs exist in this document
    unknown = set(reorder.task_ids) - set(tasks_by_id.keys())
    if unknown:
        raise AppException(
            status_code=400,
            error_code=AppErrorCode.VALIDATION_ERROR,
            detail=f"Unknown task IDs: {sorted(unknown)}",
        )

    # Slot reassignment: collect current order values, sort them,
    # then assign them in the new sequence.
    slots = sorted(tasks_by_id[tid].order for tid in reorder.task_ids)
    for slot, tid in zip(slots, reorder.task_ids, strict=True):
        t = await db.merge(tasks_by_id[tid])
        t.order = slot

    await db.commit()

    # Re-fetch all tasks ordered (full list for the event broadcast)
    result = await db.exec(select(Task).where(Task.document_id == document.id).order_by(Task.order, Task.id))
    tasks = result.all()

    await _publish_tasks_updated(events, document.id, request)

    return [TaskAdminRead.model_validate(t) for t in tasks]


@router.get("/responses", response_model=list[TaskResponseRead])
async def list_task_responses(
    db: Database,
    session_user: User = Authenticate(guards=[Guard.document_access()]),
    document: Document = Resource(Document, param_alias="document_id"),
) -> list[TaskResponseRead]:
    """Get the current user's responses for all tasks in the document."""
    # Get all tasks for the document (for correct answer revelation)
    task_result = await db.exec(select(Task).where(Task.document_id == document.id))
    tasks_by_id = {t.id: t for t in task_result.all()}

    resp_result = await db.exec(
        select(TaskResponse)
        .join(Task, TaskResponse.task_id == Task.id)
        .where(
            Task.document_id == document.id,
            TaskResponse.user_id == session_user.id,
        )
    )
    responses = resp_result.all()

    result = []
    for resp in responses:
        task = tasks_by_id.get(resp.task_id)
        correct_answer = None
        if task and not resp.is_correct and resp.attempts >= task.max_attempts:
            correct_answer = _build_correct_answer(task)

        result.append(
            TaskResponseRead(
                task_id=resp.task_id,
                user_id=resp.user_id,
                answer=resp.answer,
                is_correct=resp.is_correct,
                attempts=resp.attempts,
                correct_answer=correct_answer,
            )
        )
    return result


# ========================================================================
# ==================== Parameterised /{task_id} routes ==================
# ========================================================================


@router.get("/{task_id}")
async def get_task(
    db: Database,
    session_user: User = Authenticate(guards=[Guard.document_access()]),
    document: Document = Resource(Document, param_alias="document_id"),
    task: Task = Resource(Task, param_alias="task_id"),
) -> TaskAdminRead | TaskRead:
    """Get a single task by ID."""
    if task.document_id != document.id:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Task not found in this document",
        )
    if _is_admin(session_user, document):
        return TaskAdminRead.model_validate(task)
    return TaskRead.model_validate(task)


@router.put("/{task_id}", response_model=TaskAdminRead)
async def update_task(
    db: Database,
    events: Events,
    request: Request,
    session_user: User = Authenticate(guards=[Guard.document_access({Permission.ADMINISTRATOR})]),
    task_update: TaskUpdate = Body(...),
    document: Document = Resource(Document, param_alias="document_id"),
    task: Task = Resource(Task, param_alias="task_id"),
) -> TaskAdminRead:
    """Update a task's configuration.

    If any answer-affecting field changes (answer_type, correct
    answer, tolerance, match mode, or options), all existing
    responses are deleted so members can re-answer.
    """
    if task.document_id != document.id:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Task not found in this document",
        )

    task = await db.merge(task)

    # Determine if the correct answer is changing (for recomputation)
    answer_changed = False
    update_data = task_update.model_dump(exclude_unset=True)

    answer_fields = {
        "correct_string_answer",
        "correct_number_answer",
        "number_tolerance",
        "string_match_mode",
        "answer_type",
    }
    if answer_fields & update_data.keys():
        answer_changed = True

    # Handle options replacement separately
    new_options = update_data.pop("options", None)

    # Apply scalar updates
    task.sqlmodel_update(update_data)

    # Replace options only for multiple-choice tasks
    effective_type = task.answer_type
    if effective_type == AnswerType.MULTIPLE_CHOICE and new_options is not None:
        opts = [TaskOptionCreate(**o) for o in new_options]
        if len(opts) < 2:
            raise AppException(
                status_code=400,
                error_code=AppErrorCode.VALIDATION_ERROR,
                detail=("Multiple choice tasks require at least 2 options."),
            )
        if not any(o.is_correct for o in opts):
            raise AppException(
                status_code=400,
                error_code=AppErrorCode.VALIDATION_ERROR,
                detail=("At least one option must be marked as correct."),
            )
        await _replace_options(db, task, opts)
        answer_changed = True

    await db.flush()

    # Delete all existing responses if answer changed so members
    # can re-answer the updated task with a clean slate.
    if answer_changed:
        await db.exec(delete(TaskResponse).where(TaskResponse.task_id == task.id))

    await db.commit()
    await db.refresh(task)

    await invalidate_group_scores(document.group_id)
    await _publish_tasks_updated(events, document.id, request)

    return TaskAdminRead.model_validate(task)


@router.delete("/{task_id}")
async def delete_task(
    db: Database,
    events: Events,
    request: Request,
    session_user: User = Authenticate(guards=[Guard.document_access({Permission.ADMINISTRATOR})]),
    document: Document = Resource(Document, param_alias="document_id"),
    task: Task = Resource(Task, param_alias="task_id"),
) -> Response:
    """Delete a task (cascades to options and responses)."""
    if task.document_id != document.id:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Task not found in this document",
        )

    deleted_order = task.order
    await db.delete(task)

    # Close the gap: shift down all tasks that were after the deleted one.
    await db.exec(
        update(Task)
        .where(
            Task.document_id == document.id,
            Task.order > deleted_order,
        )
        .values(order=Task.order - 1)
    )

    await db.commit()

    await invalidate_group_scores(document.group_id)
    await _publish_tasks_updated(events, document.id, request)

    return Response(status_code=204)


# ========================================================================
# ======================= Task Responses (Member) =======================
# ========================================================================


@router.post(
    "/{task_id}/responses",
    response_model=TaskResponseRead,
    status_code=200,
)
async def submit_task_response(  # noqa: C901
    db: Database,
    session_user: User = Authenticate(guards=[Guard.document_access()]),
    response_data: TaskResponseCreate = Body(...),
    document: Document = Resource(Document, param_alias="document_id"),
    task: Task = Resource(Task, param_alias="task_id"),
) -> TaskResponseRead:
    """Submit or update a response for a task."""
    if task.document_id != document.id:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Task not found in this document",
        )

    # Load existing response with row-level lock to prevent
    # concurrent requests from bypassing the attempts check.
    existing_result = await db.exec(
        select(TaskResponse)
        .where(
            TaskResponse.task_id == task.id,
            TaskResponse.user_id == session_user.id,
        )
        .with_for_update()
    )
    existing = existing_result.first()

    # Check constraints
    if existing and existing.is_correct:
        raise AppException(
            status_code=409,
            error_code=AppErrorCode.TASK_ALREADY_CORRECT,
            detail="You have already answered this task correctly.",
        )
    if existing and existing.attempts >= task.max_attempts:
        raise AppException(
            status_code=409,
            error_code=AppErrorCode.TASK_NO_ATTEMPTS_LEFT,
            detail="No attempts remaining for this task.",
        )

    # Build answer dict based on task type
    if task.answer_type == AnswerType.MULTIPLE_CHOICE:
        if not response_data.selected_option_ids:
            raise AppException(
                status_code=400,
                error_code=AppErrorCode.VALIDATION_ERROR,
                detail=("selected_option_ids is required for MC tasks."),
            )
        # Validate option IDs belong to this task
        valid_ids = {o.id for o in task.options}
        for oid in response_data.selected_option_ids:
            if oid not in valid_ids:
                raise AppException(
                    status_code=400,
                    error_code=AppErrorCode.VALIDATION_ERROR,
                    detail=(f"Option ID {oid} does not belong to this task."),
                )
        answer = {
            "selected_option_ids": response_data.selected_option_ids,
        }

    elif task.answer_type == AnswerType.STRING:
        if response_data.text is None:
            raise AppException(
                status_code=400,
                error_code=AppErrorCode.VALIDATION_ERROR,
                detail="text is required for string tasks.",
            )
        answer = {"text": response_data.text}

    elif task.answer_type == AnswerType.NUMBER:
        if response_data.value is None:
            raise AppException(
                status_code=400,
                error_code=AppErrorCode.VALIDATION_ERROR,
                detail="value is required for number tasks.",
            )
        answer = {"value": response_data.value}
    else:
        raise AppException(
            status_code=400,
            error_code=AppErrorCode.VALIDATION_ERROR,
            detail="Unknown answer type.",
        )

    is_correct = check_task_answer(task, answer)

    if existing:
        existing = await db.merge(existing)
        existing.answer = answer
        existing.is_correct = is_correct
        existing.attempts += 1
        resp = existing
    else:
        resp = TaskResponse(
            task_id=task.id,
            user_id=session_user.id,
            answer=answer,
            is_correct=is_correct,
            attempts=1,
        )
        db.add(resp)

    await db.commit()
    await db.refresh(resp)

    # Invalidate score cache for this user only
    await invalidate_user_score(document.group_id, session_user.id)

    # Build response with optional correct answer reveal
    correct_answer = None
    if not resp.is_correct and resp.attempts >= task.max_attempts:
        correct_answer = _build_correct_answer(task)

    return TaskResponseRead(
        task_id=resp.task_id,
        user_id=resp.user_id,
        answer=resp.answer,
        is_correct=resp.is_correct,
        attempts=resp.attempts,
        correct_answer=correct_answer,
    )
