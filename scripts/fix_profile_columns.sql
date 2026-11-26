-- Correctif manuel et immédiat (Neon > SQL Editor) : ajoute les colonnes du profil avancé à accounts_user.
-- Idempotent : peut être exécuté plusieurs fois sans danger. À utiliser si vous ne voulez pas attendre le redéploiement.
BEGIN;
ALTER TABLE accounts_user
  ADD COLUMN IF NOT EXISTS username        varchar(30),
  ADD COLUMN IF NOT EXISTS avatar          varchar(100) NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS cover           varchar(100) NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS headline        varchar(100) NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS bio             text         NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS location        varchar(80)  NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS website         varchar(200) NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS github          varchar(39)  NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS twitter         varchar(15)  NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS linkedin        varchar(100) NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS profile_public  boolean      NOT NULL DEFAULT false;
-- Django fournit toujours les valeurs : on retire les DEFAULT temporaires, comme le ferait une migration.
ALTER TABLE accounts_user
  ALTER COLUMN avatar DROP DEFAULT, ALTER COLUMN cover DROP DEFAULT, ALTER COLUMN headline DROP DEFAULT,
  ALTER COLUMN bio DROP DEFAULT, ALTER COLUMN location DROP DEFAULT, ALTER COLUMN website DROP DEFAULT,
  ALTER COLUMN github DROP DEFAULT, ALTER COLUMN twitter DROP DEFAULT, ALTER COLUMN linkedin DROP DEFAULT,
  ALTER COLUMN profile_public DROP DEFAULT;
CREATE UNIQUE INDEX IF NOT EXISTS accounts_user_username_key  ON accounts_user (username);
CREATE INDEX        IF NOT EXISTS accounts_user_username_like ON accounts_user (username varchar_pattern_ops);
COMMIT;
