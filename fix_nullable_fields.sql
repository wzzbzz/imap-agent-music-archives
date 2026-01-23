-- Fix the tracks table to allow null artist
ALTER TABLE tracks ALTER COLUMN artist DROP NOT NULL;

-- Also make date_written nullable if it isn't already
ALTER TABLE tracks ALTER COLUMN date_written DROP NOT NULL;
