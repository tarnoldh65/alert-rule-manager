ALTER TABLE alert_categorizations ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE alert_categorizations ADD COLUMN autocategory_id BIGINT REFERENCES autocategories(id);
ALTER TABLE alert_categorizations ADD CONSTRAINT alert_categorizations_source_chk
    CHECK ((user_id IS NOT NULL) OR (autocategory_id IS NOT NULL));
