-- Supprime et recrée la table territories pour veilles territoriales
DROP TABLE IF EXISTS territories CASCADE;

CREATE TABLE territories (
    id          SERIAL      PRIMARY KEY,
    name        TEXT        NOT NULL,
    type        TEXT        NOT NULL DEFAULT 'commune', -- commune, departement, region, intercommunalite
    keywords    TEXT[]      NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_viewed TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_territories_type ON territories(type);
