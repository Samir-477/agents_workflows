-- Extend persisted crawl evidence for competitor research and content optimization.
-- Additive defaults keep existing page rows readable.

alter table public.pages
  add column if not exists headings_json text not null default '[]',
  add column if not exists external_links_json text not null default '[]',
  add column if not exists link_occurrences_json text not null default '[]',
  add column if not exists content_sections_json text not null default '[]',
  add column if not exists main_text text not null default '',
  add column if not exists main_text_truncated integer not null default 0,
  add column if not exists images_empty_alt integer not null default 0,
  add column if not exists images_generic_alt integer not null default 0,
  add column if not exists json_ld_errors_json text not null default '[]',
  add column if not exists content_simhash text;
