--
-- PostgreSQL database dump
--

\restrict DzWhGtAl5VZVhUbB1QfphcIElr0Ql4Zu7N7N2hwqgkab4PpAVPxUdPnhS7uyYP1

-- Dumped from database version 17.5 (Debian 17.5-1.pgdg120+1)
-- Dumped by pg_dump version 17.6 (Ubuntu 17.6-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


--
-- Data for Name: group; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public."group" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 1, 'Research Team Alpha', '78faf93a-188d-45db-9707-dbe432c33781');
INSERT INTO public."group" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 2, 'Marketing Department', '9daa44c9-2dc7-45a2-9606-4ea79f70c8e2');
INSERT INTO public."group" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 3, 'Development Squad', '16104afe-4824-4d32-a240-5e6763b8d671');
INSERT INTO public."group" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 4, 'Data Analysis Group', '2f9b11de-3fa1-4841-b233-bedab208fec9');
INSERT INTO public."group" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 5, 'Quality Assurance Team', '65b6e12c-e545-4811-b50e-ea2622258b32');
INSERT INTO public."group" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 6, 'Project Management Office', 'd0aca580-90f8-4b6d-a43e-baf24dfd1228');
INSERT INTO public."group" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 7, 'Orphaned Group', '3ef165b6-57aa-45ca-bd8d-1836b82dc44b');


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public."user" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 1, 'user1', 'John', 'Doe', '$2b$12$FmvUWuBHwz7170wxR6gvWOYCz8aRp0LDYG8IMKWF0M8kffadYd.l6', 'user1@dev.com', true);
INSERT INTO public."user" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 2, 'user2', 'Jane', 'Smith', '$2b$12$FmvUWuBHwz7170wxR6gvWOYCz8aRp0LDYG8IMKWF0M8kffadYd.l6', 'user2@dev.com', true);
INSERT INTO public."user" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 3, 'user3', 'Bob', 'Wilson', '$2b$12$FmvUWuBHwz7170wxR6gvWOYCz8aRp0LDYG8IMKWF0M8kffadYd.l6', 'user3@dev.com', true);
INSERT INTO public."user" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 4, 'user4', 'Alice', 'Brown', '$2b$12$FmvUWuBHwz7170wxR6gvWOYCz8aRp0LDYG8IMKWF0M8kffadYd.l6', 'user4@dev.com', true);
INSERT INTO public."user" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 5, 'user5', 'Charlie', 'Davis', '$2b$12$FmvUWuBHwz7170wxR6gvWOYCz8aRp0LDYG8IMKWF0M8kffadYd.l6', 'user5@dev.com', true);
INSERT INTO public."user" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 6, 'user6', 'Diana', 'Miller', '$2b$12$FmvUWuBHwz7170wxR6gvWOYCz8aRp0LDYG8IMKWF0M8kffadYd.l6', 'user6@dev.com', true);
INSERT INTO public."user" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 7, 'user7', 'Evan', 'Garcia', '$2b$12$FmvUWuBHwz7170wxR6gvWOYCz8aRp0LDYG8IMKWF0M8kffadYd.l6', 'user7@dev.com', true);
INSERT INTO public."user" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 8, 'user8', 'Fiona', 'Lopez', '$2b$12$FmvUWuBHwz7170wxR6gvWOYCz8aRp0LDYG8IMKWF0M8kffadYd.l6', 'user8@dev.com', true);
INSERT INTO public."user" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 9, 'user9', 'George', 'Taylor', '$2b$12$FmvUWuBHwz7170wxR6gvWOYCz8aRp0LDYG8IMKWF0M8kffadYd.l6', 'user9@dev.com', true);
INSERT INTO public."user" VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 10, 'user10', 'Helen', 'Clark', '$2b$12$FmvUWuBHwz7170wxR6gvWOYCz8aRp0LDYG8IMKWF0M8kffadYd.l6', 'user10@dev.com', true);


--
-- Data for Name: document; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.document VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 1, 's3://annotation-software/1.pdf', 2048, NULL, NULL);
INSERT INTO public.document VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 2, 's3://annotation-software/2.pdf', 1536, NULL, NULL);
INSERT INTO public.document VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 3, 's3://annotation-software/3.pdf', 512, NULL, NULL);
INSERT INTO public.document VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 4, 's3://annotation-software/4.pdf', 4096, NULL, NULL);
INSERT INTO public.document VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 5, 's3://annotation-software/5.pdf', 3072, NULL, NULL);
INSERT INTO public.document VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 6, 's3://annotation-software/6.pdf', 128, NULL, NULL);
INSERT INTO public.document VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 7, 's3://annotation-software/7.pdf', 128, NULL, NULL);


--
-- Data for Name: annotation; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.annotation VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 1, 1, 2, 'restricted', 15, 25, 'This annotation is restricted');
INSERT INTO public.annotation VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 2, 1, 3, 'private', 30, 10, 'This annotation is private');
INSERT INTO public.annotation VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 3, 2, 6, 'public', 5, 8, 'This annotation is public');
INSERT INTO public.annotation VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 4, 3, 9, 'public', 42, 15, 'This annotation is public');
INSERT INTO public.annotation VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 5, 4, 1, 'public', 100, 30, 'This annotation is public');
INSERT INTO public.annotation VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 6, 5, 10, 'public', 1, 5, 'This annotation is public');


--
-- Data for Name: membership; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 1, 1, 'owner');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 2, 1, 'manager');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 3, 1, 'member');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 4, 1, 'member');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 5, 2, 'owner');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 6, 2, 'member');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 7, 2, 'member');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 8, 3, 'owner');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 9, 3, 'manager');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 10, 3, 'manager');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 2, 4, 'owner');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 1, 4, 'member');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 8, 4, 'member');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 4, 5, 'owner');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 5, 5, 'manager');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 9, 5, 'member');
INSERT INTO public.membership VALUES ('2025-09-10 15:53:46.518611', '2025-09-10 15:53:46.518611', 1, 6, 'owner');


--
-- Name: annotation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.annotation_id_seq', 6, true);


--
-- Name: document_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.document_id_seq', 7, true);


--
-- Name: group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.group_id_seq', 7, true);


--
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_id_seq', 10, true);


--
-- PostgreSQL database dump complete
--

\unrestrict DzWhGtAl5VZVhUbB1QfphcIElr0Ql4Zu7N7N2hwqgkab4PpAVPxUdPnhS7uyYP1

