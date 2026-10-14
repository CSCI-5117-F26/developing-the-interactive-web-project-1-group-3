create table if not exists listing_images (
    id serial primary key,
    listing_id int not null
        references listing(id)
        on delete cascade,
    image_url text not null,
    public_id text,
    alt_text text,
    display_order int not null default 0
);

alter table listing_images
    add column if not exists public_id text;
