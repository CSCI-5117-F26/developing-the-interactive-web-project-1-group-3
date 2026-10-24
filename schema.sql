CREATE EXTENSION postgis;
create table users(
    id serial primary key,
    name text not null
);

create table listing (
    id serial primary key,
    title text not null,
    address text not null,
    location geography(Point, 4326) not null,
    rent int not null,
    leaseStart date not null,
    leaseEnd date not null,
    description text not null,
    image_data bytea,
    image_mimetype text,
    owner_id text
);

create table listing_images (
    id serial primary key,
    listing_id int not null
        references listing(id)
        on delete cascade,
    image_url text not null,
    public_id text not null,
    alt_text text,
    display_order int not null default 0
);

create table if not exists favorite (
    id serial primary key,
    listing_id int not null unique
        references listing(id)
        on delete cascade
);