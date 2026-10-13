-- 003: private Storage bucket for the review-collage maker (teach.html ข้อความ drawer).
-- Paste into Supabase -> SQL Editor -> Run, BEFORE pushing the teach.html that uploads to it. Safe to re-run.
-- Files live at  reviews/<auth.uid()>/<uuid>.jpg ; each user can only touch their own folder.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('reviews', 'reviews', false, 5242880, array['image/jpeg','image/png','image/webp'])
on conflict (id) do update set public = false, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "reviews_select" on storage.objects;
drop policy if exists "reviews_insert" on storage.objects;
drop policy if exists "reviews_update" on storage.objects;
drop policy if exists "reviews_delete" on storage.objects;
create policy "reviews_select" on storage.objects for select to authenticated
  using (bucket_id = 'reviews' and (storage.foldername(name))[1] = auth.uid()::text);
create policy "reviews_insert" on storage.objects for insert to authenticated
  with check (bucket_id = 'reviews' and (storage.foldername(name))[1] = auth.uid()::text);
create policy "reviews_update" on storage.objects for update to authenticated
  using (bucket_id = 'reviews' and (storage.foldername(name))[1] = auth.uid()::text)
  with check (bucket_id = 'reviews' and (storage.foldername(name))[1] = auth.uid()::text);
create policy "reviews_delete" on storage.objects for delete to authenticated
  using (bucket_id = 'reviews' and (storage.foldername(name))[1] = auth.uid()::text);
