-- Run on tuition_db after auditing tuition_fee.
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_tuitions_positive_fee') THEN
  ALTER TABLE tuitions ADD CONSTRAINT ck_tuitions_positive_fee CHECK (tuition_fee > 0);
 END IF;
END $$;
