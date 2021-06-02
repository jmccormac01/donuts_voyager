USE donuts;

CREATE TABLE IF NOT EXISTS autoguider_ref (
  ref_id mediumint auto_increment primary key,
  field text not null,
  telescope text not null,
  ref_image text not null,
  filter text not null,
  valid_from datetime not null,
  valid_until datetime
);

CREATE TABLE IF NOT EXISTS autoguider_log (
   updated timestamp default current_timestamp on update current_timestamp,
   night date not null,
   reference text not null,
   comparison text not null,
   stabilised int(1) not null,
   shift_x float not null,
   shift_y float not null,
   pre_pid_x float not null,
   pre_pid_y float not null,
   post_pid_x float not null,
   post_pid_y float not null,
   std_buff_x float not null,
   std_buff_y float not null,
   culled_max_shift_x int(1) not null,
   culled_max_shift_y int(1) not null
);

CREATE TABLE IF NOT EXISTS autoguider_info (
   message_id mediumint not null auto_increment primary key,
   updated timestamp default current_timestamp on update current_timestamp,
   telescope text not null,
   message text not null
);

CREATE USER 'donuts'@'%';
GRANT SELECT,INSERT ON donuts.autoguider_ref TO 'donuts'@'%';
GRANT SELECT,INSERT ON donuts.autoguider_log TO 'donuts'@'%';
GRANT SELECT,INSERT ON donuts.autoguider_info TO 'donuts'@'%';
FLUSH PRIVILEGES;
