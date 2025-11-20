<script lang="ts">
  /**
   * Combined comment component that handles both grouped and single comment UIs.
   */
  import type { CommentRead } from '$api/types';
  import type { Annotation } from '$types/pdf';
  import CommentBody from './CommentBody.svelte';
  import { fly, scale } from 'svelte/transition';
  import { quintOut } from 'svelte/easing';
	import darkModeSvelte from '$lib/stores/darkMode.svelte';

  interface Props {
    comments: CommentRead[];
    top: number;
    selectedCommentId?: number | null;
    deleteConfirmId?: number | null;
    hoverDelayMs?: number;
    expanded?: boolean;
    hovered?: boolean;
    onMouseEnter?: any;
    onMouseLeave?: any;
    onCommentSelect?: any;
    onDeleteClick?: any;
    onDeleteConfirm?: any;
    onDeleteCancel?: any;
    onClick?: any;
  }

  let {
    comments = [],
    top = 0,
    selectedCommentId = null,
    deleteConfirmId = null,
    hoverDelayMs = 200,
    expanded = false,
    hovered = false,
    onMouseEnter = () => {},
    onMouseLeave = () => {},
    onCommentSelect = () => {},
    onDeleteClick = () => {},
    onDeleteConfirm = () => {},
    onDeleteCancel = () => {},
    onClick = () => {},
  }: Props = $props();

  // Separate timers for group hover handling
  let lastGroupHoverTime = $state(0);
  let groupLeaveTimer: ReturnType<typeof setTimeout> | null = $state(null);



  // Group hover handlers that respect hoverDelayMs (mirrors CommentGroup behavior)
  function handleMouseEnter() {
    if (groupLeaveTimer) {
      clearTimeout(groupLeaveTimer);
      groupLeaveTimer = null;
    }
    lastGroupHoverTime = Date.now();
    onMouseEnter();
  }

  function handleMouseLeave() {
    const timeSinceHover = Date.now() - lastGroupHoverTime;
    const remainingDelay = Math.max(0, hoverDelayMs - timeSinceHover);

    if (remainingDelay > 0) {
      groupLeaveTimer = setTimeout(() => {
        onMouseLeave();
        groupLeaveTimer = null;
      }, remainingDelay);
    } else {
      onMouseLeave();
    }
  }

  // Active comment selection logic for group mode
  let activeComment = $derived.by(() => {
    if (selectedCommentId) {
      const found = comments.find((c) => c.id === selectedCommentId);
      return found || comments[0];
    }
    return comments[0];
  });

  let activeAnnotation = $derived(activeComment.annotation as unknown as Annotation);


</script>

{#if expanded || hovered}
  <!-- Expanded container used for both group and single comment expanded states -->
  <div
    class="absolute left-4 right-2 z-20 overflow-visible rounded-lg border-l-4 bg-inset shadow-lg"
    style:top="{top}px"
    style:border-left-color={activeAnnotation.color}
    onmouseenter={handleMouseEnter}
    onmouseleave={handleMouseLeave}
    onclick={onClick}
    onkeydown={(e) => {
      // Don't prevent default if user is typing in an input/textarea
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        return;
      }
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        (onClick)(e as any);
      }
    }}
    role="button"
    tabindex="0"
    in:fly={{ x: -20, duration: 250, easing: quintOut }}
    out:fly={{ x: -20, duration: 200, easing: quintOut }}
  >
    {#if comments.length > 1}
      <div class="flex flex-wrap gap-1 border-b border-text/10 px-3 pt-2">
        {#each comments as comment (comment.id)}
          {@const annotation = comment.annotation as unknown as Annotation}
          {@const isActive = activeComment.id === comment.id}
          <button
            class="flex items-center gap-1.5 rounded-t-md px-2.5 py-1 text-xs font-medium transition-all {isActive ? 'bg-inset text-text border-t border-x border-text/20 -mb-px' : 'bg-background text-text/60'}"
            style:border-bottom={isActive ? '2px solid var(--color-inset)' : 'none'}
            onclick={(e) => {
              e.stopPropagation();
              onCommentSelect(comment.id);
            }}
          >
            <div class="h-2.5 w-2.5 rounded-full" style:background-color={annotation.color}></div>
            <span>{comment.user?.username?.[0]?.toUpperCase() ?? '?'}</span>
          </button>
        {/each}
      </div>
    {/if}

    <div class="px-4 py-3">
      <CommentBody
        comment={activeComment}
        annotation={activeAnnotation}
        showDeleteConfirm={deleteConfirmId === activeComment.id}
        onDeleteClick={(e) =>  onDeleteClick(activeComment.id, e)}
        onDeleteConfirm={(e) => onDeleteConfirm(activeComment.id, e)}
        {onDeleteCancel}
      />
    </div>
  </div>
{:else}
  <!-- Collapsed badge for either group (count) or single (initial) -->
    {@const annotation = comments[0]?.annotation as unknown as Annotation}
    {@const badgeColor = annotation?.color ?? '#ccc'}
    <div
      class="absolute left-4 right-2 z-10 flex max-w-full justify-end"
      style:top="{top}px"
      onmouseenter={handleMouseEnter}
      onmouseleave={handleMouseLeave}
      role="button"
      tabindex="0"
      in:scale={{ duration: 200, start: 0.8, easing: quintOut }}
      out:scale={{ duration: 150, start: 0.8, easing: quintOut }}
    >
      <div
        class="cursor-pointer rounded-sm px-2.5 py-1 transition-all duration-200 shadow-lg opacity-100"
        style:background-color={badgeColor}
      >
        <span
          class="font-bold text-inset shadow-black {darkModeSvelte.enabled ? '' : 'text-shadow-lg'}"
        >
          {comments.length === 1
            ? comments[0]?.user?.username[0]?.toUpperCase() ?? "?"
            : comments.length}
        </span>
      </div>
    </div>
{/if}

<style>
  :global(.comment-sidebar) :global(svg) {
    overflow: visible;
  }
</style>
