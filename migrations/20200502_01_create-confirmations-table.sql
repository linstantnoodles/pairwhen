CREATE TABLE `confirmations` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `time_id` int(11) NOT NULL,
    `guest_email` varchar(255) NOT NULL,
    `timezone` varchar(255) NULL,
    `host_accepted` BOOLEAN NULL,
     PRIMARY KEY (`id`),
     INDEX meeting_id_index (`time_id`),
     FOREIGN KEY (`time_id`)
        REFERENCES available_times(`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;