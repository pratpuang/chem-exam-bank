-- 002: free-text notes per student (Notion's หัวข้อย่อย + หมายเหตุ land here)
alter table students add column if not exists notes text default '';
