create table if not exists card_users
(
    Data_vremya      timestamp default current_timestamp(0),
    Id_user          bigint,
    status           text,
    inputs           int
);