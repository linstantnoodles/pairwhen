CREATE TABLE `available_times` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `meeting_id` int(11) NOT NULL ,
    `start_datetime` DATETIME NOT NULL,
    `end_datetime` DATETIME NOT NULL,
    `start_datetime_utc` DATETIME NOT NULL,
    `end_datetime_utc` DATETIME NOT NULL,
    `timezone` varchar(255) NULL,
     PRIMARY KEY (`id`),
     INDEX meeting_id_index (`meeting_id`),
     FOREIGN KEY (`meeting_id`)
        REFERENCES meetings(`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;