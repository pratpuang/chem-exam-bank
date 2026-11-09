-- 2026-11-09: let the hourly rate be fractional (e.g. 400 baht for a 1.5 h class = 266.666.../hr).
-- Paste into Supabase -> SQL Editor -> Run, BEFORE pushing the teach.html that lets you type a rate.
alter table students alter column rate type numeric;
alter table sessions alter column rate type numeric;
