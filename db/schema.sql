-- Core X — transcript / knowledge-base schema (MySQL 8 / MariaDB).
-- REFERENCE ONLY. The Laravel migrations in admin/database/migrations are the
-- source of truth; this mirrors them for the Python runtime and manual setup.
--
--   mysql -u root < db/schema.sql

CREATE DATABASE IF NOT EXISTS corex CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE corex;

CREATE TABLE IF NOT EXISTS bots (
  id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  slug              VARCHAR(120) NOT NULL UNIQUE,          -- == BOT_ID in the runtime .env
  name              VARCHAR(190) NOT NULL,
  property_name     VARCHAR(190) NULL,
  address           VARCHAR(255) NULL,
  tavus_persona_id  VARCHAR(120) NULL,
  tavus_replica_id  VARCHAR(120) NULL,
  kb_base_context   LONGTEXT NULL,
  active            TINYINT(1) NOT NULL DEFAULT 1,
  created_at        TIMESTAMP NULL,
  updated_at        TIMESTAMP NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS conversations (
  id                    BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  bot_id                BIGINT UNSIGNED NOT NULL,
  tavus_conversation_id VARCHAR(120) NOT NULL UNIQUE,
  source                VARCHAR(40) NULL,                  -- kiosk | manual
  status                VARCHAR(40) NULL,                  -- active | ended
  started_at            TIMESTAMP NULL,
  ended_at              TIMESTAMP NULL,
  duration_seconds      INT NULL,
  raw_transcript        LONGTEXT NULL,
  created_at            TIMESTAMP NULL,
  updated_at            TIMESTAMP NULL,
  INDEX (bot_id),
  CONSTRAINT fk_conv_bot FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transcript_messages (
  id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  conversation_id  BIGINT UNSIGNED NOT NULL,
  turn_index       INT NOT NULL,
  role             VARCHAR(20) NOT NULL,                   -- visitor | assistant
  content          LONGTEXT NOT NULL,
  spoken_at        VARCHAR(64) NULL,
  created_at       TIMESTAMP NULL,
  updated_at       TIMESTAMP NULL,
  INDEX (conversation_id),
  CONSTRAINT fk_msg_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS deflection_phrases (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  bot_id      BIGINT UNSIGNED NULL,                        -- NULL = global
  phrase      VARCHAR(255) NOT NULL,
  match_type  VARCHAR(20) NOT NULL DEFAULT 'contains',     -- contains | regex
  active      TINYINT(1) NOT NULL DEFAULT 1,
  created_at  TIMESTAMP NULL,
  updated_at  TIMESTAMP NULL,
  CONSTRAINT fk_phrase_bot FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS unanswered_questions (
  id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  bot_id           BIGINT UNSIGNED NOT NULL,
  conversation_id  BIGINT UNSIGNED NULL,
  question         LONGTEXT NOT NULL,
  context_excerpt  LONGTEXT NULL,
  source           VARCHAR(40) NOT NULL,                   -- deflection_phrase | escalation
  matched_phrase   VARCHAR(255) NULL,
  status           VARCHAR(40) NOT NULL DEFAULT 'pending', -- pending|answered|approved|rejected|published
  dedup_hash       VARCHAR(64) NOT NULL,
  created_at       TIMESTAMP NULL,
  updated_at       TIMESTAMP NULL,
  UNIQUE KEY uq_unanswered_bot_dedup (bot_id, dedup_hash),
  INDEX (bot_id, status),
  CONSTRAINT fk_uq_bot FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE,
  CONSTRAINT fk_uq_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS knowledge_answers (
  id                      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  unanswered_question_id  BIGINT UNSIGNED NULL,
  bot_id                  BIGINT UNSIGNED NOT NULL,
  question                LONGTEXT NOT NULL,
  answer                  LONGTEXT NOT NULL,
  authored_by             VARCHAR(190) NULL,
  status                  VARCHAR(40) NOT NULL DEFAULT 'draft', -- draft|pending_approval|approved|rejected|published
  reviewed_by             VARCHAR(190) NULL,
  reject_reason           VARCHAR(255) NULL,
  approved_at             TIMESTAMP NULL,
  published_at            TIMESTAMP NULL,
  created_at              TIMESTAMP NULL,
  updated_at              TIMESTAMP NULL,
  INDEX (bot_id, status),
  CONSTRAINT fk_ka_uq FOREIGN KEY (unanswered_question_id) REFERENCES unanswered_questions(id) ON DELETE SET NULL,
  CONSTRAINT fk_ka_bot FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
) ENGINE=InnoDB;
