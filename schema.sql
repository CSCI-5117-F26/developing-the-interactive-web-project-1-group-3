create table users(
    id serial primary key,
    name text not null, 
);

create table listing (
    id serial primary key,
    title text not null,
    address text not null,
    rent int not null,
    leaseStart date not null,
    leaseEnd date not null,
    description text not null
);