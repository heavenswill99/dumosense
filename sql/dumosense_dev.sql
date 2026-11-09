-- ============================================================
-- DUMOSENSE MVP DATABASE SCHEMA
-- MindGuard + Health Reserve + Shared Intelligence Foundation
-- ============================================================

CREATE DATABASE dumosense_dev;
USE dumosense_dev;

-- 1. USERS
-- Root/parent table for every Dumosense user.
-- Most user-related tables connect back to this table.
-- ============================================================

CREATE TABLE users (
    user_id VARCHAR(20) PRIMARY KEY NOT NULL, -- Unique ID for each user
    first_name VARCHAR(100) NOT NULL,         -- User's first name
    last_name VARCHAR(100) NOT NULL,          -- User's last name
    email VARCHAR(255) NOT NULL UNIQUE,       -- Unique email address
    account_status VARCHAR(20) NOT NULL,      -- e.g. active, inactive
    created_at DATETIME NOT NULL,             -- When account was created
    updated_at DATETIME NOT NULL,             -- Last account update

    -- INDEX improves searches/filtering using account_status.
    -- Example: WHERE account_status = 'active'
    -- It does NOT create a relationship between tables.
    INDEX idx_users_status (account_status)
);


-- 2. ASSESSMENT TYPES
-- Defines the types/domains of cognitive assessments available.
-- Parent of cognitive_tasks and assessment_sessions.
-- ============================================================

CREATE TABLE assessment_types (
    assessment_type_id VARCHAR(20) PRIMARY KEY,
    assessment_name VARCHAR(100) NOT NULL,
    cognitive_domain VARCHAR(50) NOT NULL,
    description VARCHAR(500),
    active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Speeds up searches/filtering by cognitive domain.
    INDEX idx_assessment_domain (cognitive_domain)
);


-- 3. COGNITIVE TASKS
-- Stores individual cognitive tasks used in assessments.
-- Relationship:
-- assessment_types 1 ----< cognitive_tasks
-- One assessment type can contain many cognitive tasks.
-- ============================================================

CREATE TABLE cognitive_tasks (
    task_id VARCHAR(20) PRIMARY KEY,
    assessment_type_id VARCHAR(20) NOT NULL,
    task_name VARCHAR(100) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    default_difficulty TINYINT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Connects each task to its assessment type.
    CONSTRAINT fk_task_assessment_type
        FOREIGN KEY (assessment_type_id)
        REFERENCES assessment_types(assessment_type_id),

    -- Speeds up finding tasks belonging to an assessment type.
    INDEX idx_task_assessment_type (assessment_type_id)
);


-- 4. USER PROFILES
-- Stores demographic/profile information separately from login and account identity information.
-- Relationship:
-- users 1 ---- 1 user_profiles
-- Each user can have only one profile.
-- ============================================================

CREATE TABLE user_profiles (
    profile_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    date_of_birth DATE NOT NULL,
    age_group VARCHAR(20),
    sex VARCHAR(20),
    country VARCHAR(100),
    state_or_region VARCHAR(100),
    profile_status VARCHAR(20) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,

    -- Connects the profile to the user who owns it.
    CONSTRAINT fk_profile_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    -- Prevents one user from having multiple profile rows.
    CONSTRAINT uq_profile_user
        UNIQUE (user_id)
);


-- 5. PRODUCT ENROLLMENTS
-- Records which Dumosense products a user is enrolled in, e.g. MINDGUARD or HEALTH_RESERVE.
-- Relationship:
-- users 1 ----< product_enrollments
-- One user may be enrolled in multiple products.
-- ============================================================

CREATE TABLE product_enrollments (
    enrollment_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    product_code VARCHAR(30) NOT NULL,
    enrollment_status VARCHAR(20) NOT NULL,
    enrolled_at DATETIME NOT NULL,
    discontinued_at DATETIME NULL,

    -- Connects enrollment to the user.
    CONSTRAINT fk_enrollment_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    -- Prevents duplicate enrollment in the same product.
    CONSTRAINT uq_user_product
        UNIQUE (user_id, product_code),

    -- Indexes improve filtering by product and enrollment status.
    INDEX idx_enrollment_product (product_code),
    INDEX idx_enrollment_status (enrollment_status)
);


-- 6. CONSENTS
-- Records what a user has permitted Dumosense to do with data.
-- Relationship:
-- users 1 ----< consents
-- One user can have multiple consent records/purposes.
-- ============================================================

CREATE TABLE consents (
    consent_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    consent_type VARCHAR(100) NOT NULL,
    purpose VARCHAR(255) NOT NULL,
    consent_version DECIMAL(5,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    granted_at DATETIME NOT NULL,
    withdrawn_at DATETIME NULL,

    -- Identifies the user who owns/gave the consent.
    CONSTRAINT fk_consent_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    -- Indexes speed up consent lookups.
    INDEX idx_consent_user (user_id),
    INDEX idx_consent_type (consent_type),
    INDEX idx_consent_status (status)
);


-- 7. CONSENT HISTORY
-- Keeps the history of changes to a user's consent.
-- Relationships:
-- consents 1 ----< consent_history
-- users    1 ----< consent_history
-- This allows us to know what changed, when and for whom.
-- ============================================================

CREATE TABLE consent_history (
    consent_history_id VARCHAR(20) PRIMARY KEY,
    consent_id VARCHAR(20) NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    previous_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_at DATETIME NOT NULL,
    reason VARCHAR(255),

    -- Identifies the consent record that changed.
    CONSTRAINT fk_consent_history_consent
        FOREIGN KEY (consent_id)
        REFERENCES consents(consent_id),

    -- Identifies the user whose consent changed.
    CONSTRAINT fk_consent_history_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    -- Indexes improve searches by consent, user and date.
    INDEX idx_consent_history_consent (consent_id),
    INDEX idx_consent_history_user (user_id),
    INDEX idx_consent_history_changed (changed_at)
);


-- ============================================================
-- 8. ASSESSMENT SESSIONS
-- Records each time a user starts/completes an assessment.
-- Relationships:
-- users            1 ----< assessment_sessions
-- assessment_types 1 ----< assessment_sessions
-- consents         1 ----< assessment_sessions
-- This lets us know WHO took WHAT assessment, WHEN, and under WHICH consent.
-- ============================================================

CREATE TABLE assessment_sessions (
    session_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    assessment_type_id VARCHAR(20) NOT NULL,
    started_at DATETIME NOT NULL,
    completed_at DATETIME NULL,
    session_status VARCHAR(20) NOT NULL,
    difficulty_level TINYINT NOT NULL,
    device_type VARCHAR(30),
    consent_id VARCHAR(20) NOT NULL,

    CONSTRAINT fk_session_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    CONSTRAINT fk_session_assessment
        FOREIGN KEY (assessment_type_id)
        REFERENCES assessment_types(assessment_type_id),

    CONSTRAINT fk_session_consent
        FOREIGN KEY (consent_id)
        REFERENCES consents(consent_id),

    -- Composite index helps retrieve a user's sessions over time.
    INDEX idx_session_user_date (user_id, started_at),

    INDEX idx_session_assessment (assessment_type_id),
    INDEX idx_session_status (session_status)
);


-- 9. COGNITIVE RESPONSES
-- Stores raw trial-level responses from cognitive tasks.
-- Relationships:
-- assessment_sessions 1 ----< cognitive_responses
-- cognitive_tasks     1 ----< cognitive_responses
-- One assessment session contains many individual responses.
-- ============================================================

CREATE TABLE cognitive_responses (
    response_id VARCHAR(20) PRIMARY KEY,
    session_id VARCHAR(20) NOT NULL,
    task_id VARCHAR(20) NOT NULL,
    trial_number INT NOT NULL,
    stimulus_type VARCHAR(50),
    response_type VARCHAR(50),
    is_correct BOOLEAN NOT NULL,
    reaction_time_ms DECIMAL(10,2),
    response_value VARCHAR(255),
    omission BOOLEAN NOT NULL DEFAULT FALSE,
    recorded_at DATETIME NOT NULL,

    CONSTRAINT fk_response_session
        FOREIGN KEY (session_id)
        REFERENCES assessment_sessions(session_id),

    CONSTRAINT fk_response_task
        FOREIGN KEY (task_id)
        REFERENCES cognitive_tasks(task_id),

    INDEX idx_response_session (session_id),
    INDEX idx_response_task (task_id),

    -- Helps retrieve trials in a particular session efficiently.
    INDEX idx_response_session_trial (session_id, trial_number)
);


-- 10. COGNITIVE RESULTS
-- Stores calculated summary results for an assessment session.
-- Relationships:
-- assessment_sessions 1 ---- 1 cognitive_results
-- users               1 ----< cognitive_results
-- assessment_types    1 ----< cognitive_results
-- Raw responses are summarized into metrics such as accuracy, reaction time and change from baseline.
-- ============================================================

CREATE TABLE cognitive_results (
    cognitive_result_id VARCHAR(20) PRIMARY KEY,
    session_id VARCHAR(20) NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    assessment_type_id VARCHAR(20) NOT NULL,
    total_trials INT NOT NULL,
    correct_responses INT NOT NULL,
    incorrect_responses INT NOT NULL,
    omissions INT NOT NULL,
    accuracy_rate DECIMAL(8,6),
    mean_reaction_time_ms DECIMAL(10,2),
    median_reaction_time_ms DECIMAL(10,2),
    reaction_time_variability_ms DECIMAL(10,2),
    completion_time_seconds DECIMAL(10,2),
    difficulty_level TINYINT,
    baseline_difference DECIMAL(10,6),
    previous_session_difference DECIMAL(10,6),
    calculated_at DATETIME NOT NULL,

    CONSTRAINT fk_result_session
        FOREIGN KEY (session_id)
        REFERENCES assessment_sessions(session_id),

    CONSTRAINT fk_result_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    CONSTRAINT fk_result_assessment
        FOREIGN KEY (assessment_type_id)
        REFERENCES assessment_types(assessment_type_id),

    -- Ensures one summary result per assessment session.
    CONSTRAINT uq_result_session
        UNIQUE (session_id),

    -- Helps retrieve a user's cognitive results chronologically.
    INDEX idx_result_user_date (user_id, calculated_at),

    INDEX idx_result_domain (assessment_type_id)
);



-- 11. WELLBEING CHECK-INS
-- Stores repeated wellbeing observations such as mood, stress, anxiety and sleep.
-- Relationship:
-- users 1 ----< wellbeing_checkins
-- One user can have many check-ins over time.
-- ============================================================

CREATE TABLE wellbeing_checkins (
    checkin_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    recorded_at DATETIME NOT NULL,
    mood_level DECIMAL(4,2),
    stress_level DECIMAL(4,2),
    anxiety_level DECIMAL(4,2),
    sleep_quality DECIMAL(4,2),
    sleep_hours DECIMAL(4,2),
    social_wellbeing DECIMAL(4,2),
    perceived_cognitive_change DECIMAL(4,2),
    completion_status VARCHAR(20) NOT NULL,

    CONSTRAINT fk_wellbeing_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    -- Useful for retrieving a user's wellbeing history by date.
    INDEX idx_wellbeing_user_date (user_id, recorded_at)
);


-- ============================================================
-- 12. CONTEXT RECORDS
-- Stores contextual factors that may help explain changes, such as sleep, stress or other relevant circumstances.
-- Relationships:
-- users               1 ----< context_records
-- assessment_sessions 1 ----< context_records (optional)
-- related_session_id is nullable because context may exist without being linked to a specific assessment session.
-- ============================================================

CREATE TABLE context_records (
    context_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    related_session_id VARCHAR(20) NULL,
    recorded_at DATETIME NOT NULL,
    context_type VARCHAR(50) NOT NULL,
    context_value VARCHAR(255),
    source VARCHAR(50) NOT NULL,

    CONSTRAINT fk_context_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    CONSTRAINT fk_context_session
        FOREIGN KEY (related_session_id)
        REFERENCES assessment_sessions(session_id),

    INDEX idx_context_user_date (user_id, recorded_at),
    INDEX idx_context_type (context_type)
);


-- 13. HEALTH RESERVE ASSESSMENTS
-- Stores a user's financial health-preparedness assessments.
-- Relationship:
-- users 1 ----< health_reserve_assessments
-- Multiple assessments allow preparedness to be tracked longitudinally over time.
-- ============================================================

CREATE TABLE health_reserve_assessments (
    reserve_assessment_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    assessed_at DATETIME NOT NULL,
    healthcare_coverage_status VARCHAR(30) NOT NULL,
    estimated_healthcare_exposure DECIMAL(15,2) NOT NULL,
    emergency_health_resources DECIMAL(15,2) NOT NULL,
    monthly_financial_obligations DECIMAL(15,2) NOT NULL,
    number_of_dependants INT NOT NULL,
    current_preparedness_amount DECIMAL(15,2) NOT NULL,
    preparedness_target DECIMAL(15,2) NOT NULL,
    preparedness_gap DECIMAL(15,2) NOT NULL,
    preparedness_ratio DECIMAL(10,6) NOT NULL,
    reserve_status VARCHAR(30) NOT NULL,

    CONSTRAINT fk_reserve_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    -- Helps retrieve a user's preparedness history over time.
    INDEX idx_reserve_user_date (user_id, assessed_at),

    INDEX idx_reserve_status (reserve_status)
);


-- 14. EVENTS
-- Records important actions/events occurring in Dumosense.
-- Examples: assessment_completed, consent_granted, insight_generated or recommendation_viewed.
-- Relationship:
-- users 1 ----< events
-- ============================================================

CREATE TABLE events (
    event_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    timestamp DATETIME NOT NULL,
    source VARCHAR(50) NOT NULL,
    related_entity_type VARCHAR(50),
    related_entity_id VARCHAR(50),
    metadata JSON,

    CONSTRAINT fk_event_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    -- Finds a user's events chronologically.
    INDEX idx_event_user_time (user_id, timestamp),

    -- Finds events of a particular type.
    INDEX idx_event_type (event_type),

    -- Helps locate events related to another entity.
    INDEX idx_event_entity (related_entity_type, related_entity_id)
);


-- 15. INTELLIGENCE RUNS
-- Records each execution of a Dumosense model/rule.
-- Important for AI traceability and reproducibility.
-- Relationship:
-- users 1 ----< intelligence_runs
-- Records which user, product, model/rule version and input period were involved in an intelligence run.
-- ============================================================

CREATE TABLE intelligence_runs (
    run_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    product_code VARCHAR(30) NOT NULL,
    triggered_at DATETIME NOT NULL,
    trigger_type VARCHAR(50) NOT NULL,
    model_or_rule_version VARCHAR(100) NOT NULL,
    input_start_date DATETIME,
    input_end_date DATETIME,
    run_status VARCHAR(30) NOT NULL,

    CONSTRAINT fk_run_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    INDEX idx_run_user_product (user_id, product_code),
    INDEX idx_run_triggered (triggered_at),
    INDEX idx_run_model_version (model_or_rule_version)
);


-- ============================================================
-- 16. INSIGHTS
-- Stores observations/intelligence produced by a model or rule.
-- Relationships:
-- intelligence_runs 1 ----< insights
-- users             1 ----< insights
-- This allows every insight to be traced back to the run that generated it.
-- ============================================================

CREATE TABLE insights (
    insight_id VARCHAR(20) PRIMARY KEY,
    run_id VARCHAR(20) NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    product_code VARCHAR(30) NOT NULL,
    insight_type VARCHAR(100) NOT NULL,
    insight_text TEXT NOT NULL,
    severity_or_priority VARCHAR(20),
    explanation_text TEXT,
    generated_at DATETIME NOT NULL,

    CONSTRAINT fk_insight_run
        FOREIGN KEY (run_id)
        REFERENCES intelligence_runs(run_id),

    CONSTRAINT fk_insight_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    INDEX idx_insight_user_product (user_id, product_code),
    INDEX idx_insight_type (insight_type),
    INDEX idx_insight_generated (generated_at)
);


-- 17. RECOMMENDATIONS
-- Stores recommended next steps generated from insights.
-- Relationships:
-- insights 1 ----< recommendations
-- users    1 ----< recommendations
-- Separating insights and recommendations allows Dumosense to distinguish "what was observed" from "what to do next."
-- ============================================================

CREATE TABLE recommendations (
    recommendation_id VARCHAR(20) PRIMARY KEY,
    insight_id VARCHAR(20) NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    product_code VARCHAR(30) NOT NULL,
    recommendation_type VARCHAR(100) NOT NULL,
    recommendation_text TEXT NOT NULL,
    priority VARCHAR(20),
    created_at DATETIME NOT NULL,

    CONSTRAINT fk_recommendation_insight
        FOREIGN KEY (insight_id)
        REFERENCES insights(insight_id),

    CONSTRAINT fk_recommendation_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    INDEX idx_recommendation_user_product (user_id, product_code),
    INDEX idx_recommendation_created (created_at)
);



-- 18. ACTIONS
-- Records what happened after a recommendation.
-- Relationships:
-- recommendations 1 ----< actions
-- users           1 ----< actions
-- This closes the intelligence loop: insight -> recommendation -> user action.
-- ============================================================

CREATE TABLE actions (
    action_id VARCHAR(20) PRIMARY KEY,
    recommendation_id VARCHAR(20) NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_status VARCHAR(50) NOT NULL,
    action_at DATETIME NOT NULL,

    CONSTRAINT fk_action_recommendation
        FOREIGN KEY (recommendation_id)
        REFERENCES recommendations(recommendation_id),

    CONSTRAINT fk_action_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    INDEX idx_action_user_date (user_id, action_at),
    INDEX idx_action_recommendation (recommendation_id)
);


-- 19. AUDIT LOGS
-- Records important system/data actions for accountability,governance and security.
-- Relationship: users 1 ----< audit_logs
-- actor_user_id identifies the user responsible for an action.
-- It is nullable so future system/service actions can also be represented.
-- ============================================================

CREATE TABLE audit_logs (
    audit_id VARCHAR(20) PRIMARY KEY,
    actor_user_id VARCHAR(20),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(50),
    timestamp DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL,

    CONSTRAINT fk_audit_actor
        FOREIGN KEY (actor_user_id)
        REFERENCES users(user_id),

    -- Finds audit activity performed by a user over time.
    INDEX idx_audit_actor_time (actor_user_id, timestamp),

    -- Finds audit records concerning a particular resource.
    INDEX idx_audit_resource (resource_type, resource_id),

    -- Finds audit records by action type.
    INDEX idx_audit_action (action)
);

SHOW TABLES;

DESCRIBE users;
 
SELECT
    TABLE_NAME,
    COLUMN_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'dumosense_dev'
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME;

SHOW VARIABLES LIKE 'local_infile';
SET GLOBAL local_infile = 1;

-- ============LOADING DATA INFILE===========

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/assessment_types.csv'
INTO TABLE assessment_types
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    assessment_type_id,
    assessment_name,
    cognitive_domain,
    `description`,
    `active`
);

-- 3. COGNITIVE TASKS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/cognitive_tasks.csv'
INTO TABLE cognitive_tasks
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    task_id,
    assessment_type_id,
    task_name,
    task_type,
    default_difficulty,
    active
);

-- 4. USER PROFILES
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/user_profiles.csv'
INTO TABLE user_profiles
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    profile_id,
    user_id,
    @date_of_birth,
    age_group,
    sex,
    country,
    state_or_region,
    profile_status,
    @created_at,
    @updated_at
)
SET
    date_of_birth = STR_TO_DATE(@date_of_birth, '%Y-%m-%d'),
    created_at = STR_TO_DATE(@created_at, '%Y-%m-%dT%H:%i:%s'),
    updated_at = STR_TO_DATE(@updated_at, '%Y-%m-%dT%H:%i:%s');
    
SELECT * from user_profiles;

-- 5. PRODUCT ENROLLMENTS
-- Depends on users
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/product_enrollments.csv'
INTO TABLE product_enrollments
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    enrollment_id,
    user_id,
    product_code,
    enrollment_status,
    @enrolled_at,
    @discontinued_at
)
SET
    enrolled_at = STR_TO_DATE(@enrolled_at, '%Y-%m-%dT%H:%i:%s'),
    discontinued_at =
        CASE
            WHEN NULLIF(TRIM(@discontinued_at), '') IS NULL THEN NULL
            ELSE STR_TO_DATE(@discontinued_at, '%Y-%m-%dT%H:%i:%s')
        END;
        
-- 6. CONSENTS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/consents.csv'
INTO TABLE consents
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    consent_id,
    user_id,
    consent_type,
    purpose,
    consent_version,
    status,
    @granted_at,
    @withdrawn_at
)
SET
    granted_at = STR_TO_DATE(@granted_at, '%Y-%m-%dT%H:%i:%s'),
    withdrawn_at =
        CASE
            WHEN NULLIF(TRIM(@withdrawn_at), '') IS NULL THEN NULL
            ELSE STR_TO_DATE(@withdrawn_at, '%Y-%m-%dT%H:%i:%s')
        END;
        

-- 7. CONSENT HISTORY
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/consent_history.csv'
INTO TABLE consent_history
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    consent_history_id,
    consent_id,
    user_id,
    @previous_status,
    new_status,
    @changed_at,
    @reason
)
SET
    previous_status = NULLIF(TRIM(@previous_status), ''),
    changed_at = STR_TO_DATE(@changed_at, '%Y-%m-%dT%H:%i:%s'),
    reason = NULLIF(TRIM(@reason), '');
    
-- 8. ASSESSMENT SESSIONS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/assessment_sessions.csv'
INTO TABLE assessment_sessions
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    session_id,
    user_id,
    assessment_type_id,
    @started_at,
    @completed_at,
    session_status,
    difficulty_level,
    device_type,
    consent_id
)
SET
    started_at = STR_TO_DATE(@started_at, '%Y-%m-%dT%H:%i:%s'),
    completed_at =
        CASE
            WHEN NULLIF(TRIM(@completed_at), '') IS NULL THEN NULL
            ELSE STR_TO_DATE(@completed_at, '%Y-%m-%dT%H:%i:%s')
        END;
        

-- LARGE FILE - APPROX. 770,000 ROWS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/cognitive_responses.csv'
INTO TABLE cognitive_responses
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    response_id,
    session_id,
    task_id,
    trial_number,
    stimulus_type,
    response_type,
    is_correct,
    @reaction_time_ms,
    @response_value,
    omission,
    @recorded_at
)
SET
    reaction_time_ms = NULLIF(TRIM(@reaction_time_ms), ''),
    response_value = NULLIF(TRIM(@response_value), ''),
    recorded_at = STR_TO_DATE(@recorded_at, '%Y-%m-%dT%H:%i:%s');

-- 10. COGNITIVE RESULTS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/cognitive_results.csv'
INTO TABLE cognitive_results
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    cognitive_result_id,
    session_id,
    user_id,
    assessment_type_id,
    total_trials,
    correct_responses,
    incorrect_responses,
    omissions,
    @accuracy_rate,
    @mean_reaction_time_ms,
    @median_reaction_time_ms,
    @reaction_time_variability_ms,
    @completion_time_seconds,
    difficulty_level,
    @baseline_difference,
    @previous_session_difference,
    @calculated_at
)
SET
    accuracy_rate = NULLIF(TRIM(@accuracy_rate), ''),
    mean_reaction_time_ms = NULLIF(TRIM(@mean_reaction_time_ms), ''),
    median_reaction_time_ms = NULLIF(TRIM(@median_reaction_time_ms), ''),
    reaction_time_variability_ms =
        NULLIF(TRIM(@reaction_time_variability_ms), ''),
    completion_time_seconds =
        NULLIF(TRIM(@completion_time_seconds), ''),
    baseline_difference =
        NULLIF(TRIM(@baseline_difference), ''),
    previous_session_difference =
        NULLIF(TRIM(@previous_session_difference), ''),
    calculated_at =
        STR_TO_DATE(@calculated_at, '%Y-%m-%dT%H:%i:%s');



-- 11. WELLBEING CHECKINS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/wellbeing_checkins.csv'
INTO TABLE wellbeing_checkins
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    checkin_id,
    user_id,
    @recorded_at,
    @mood_level,
    @stress_level,
    @anxiety_level,
    @sleep_quality,
    @sleep_hours,
    @social_wellbeing,
    @perceived_cognitive_change,
    completion_status
)
SET
    recorded_at =
        STR_TO_DATE(@recorded_at, '%Y-%m-%dT%H:%i:%s'),
    mood_level =
        NULLIF(TRIM(@mood_level), ''),
    stress_level =
        NULLIF(TRIM(@stress_level), ''),
    anxiety_level =
        NULLIF(TRIM(@anxiety_level), ''),
    sleep_quality =
        NULLIF(TRIM(@sleep_quality), ''),
    sleep_hours =
        NULLIF(TRIM(@sleep_hours), ''),
    social_wellbeing =
        NULLIF(TRIM(@social_wellbeing), ''),
    perceived_cognitive_change =
        NULLIF(TRIM(@perceived_cognitive_change), '');


-- 12. CONTEXT RECORDS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/context_records.csv'
INTO TABLE context_records
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    context_id,
    user_id,
    @related_session_id,
    @recorded_at,
    context_type,
    @context_value,
    source
)
SET
    related_session_id =
        NULLIF(TRIM(@related_session_id), ''),
    recorded_at =
        STR_TO_DATE(@recorded_at, '%Y-%m-%dT%H:%i:%s'),
    context_value =
        NULLIF(TRIM(@context_value), '');



-- 13. HEALTH RESERVE ASSESSMENTS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/health_reserve_assessments.csv'
INTO TABLE health_reserve_assessments
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    reserve_assessment_id,
    user_id,
    @assessed_at,
    healthcare_coverage_status,
    estimated_healthcare_exposure,
    emergency_health_resources,
    monthly_financial_obligations,
    number_of_dependants,
    current_preparedness_amount,
    preparedness_target,
    preparedness_gap,
    preparedness_ratio,
    reserve_status
)
SET
    assessed_at =
        STR_TO_DATE(@assessed_at, '%Y-%m-%dT%H:%i:%s');


-- 14. EVENTS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/events.csv'
INTO TABLE events
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    event_id,
    user_id,
    event_type,
    @event_timestamp,
    source,
    @related_entity_type,
    @related_entity_id,
    @metadata
)
SET
    timestamp =
        STR_TO_DATE(@event_timestamp, '%Y-%m-%dT%H:%i:%s'),
    related_entity_type =
        NULLIF(TRIM(@related_entity_type), ''),
    related_entity_id =
        NULLIF(TRIM(@related_entity_id), ''),
    metadata =
        CASE
            WHEN NULLIF(TRIM(@metadata), '') IS NULL THEN NULL
            ELSE @metadata
        END;


-- 15. INTELLIGENCE RUNS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/intelligence_runs.csv'
INTO TABLE intelligence_runs
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    run_id,
    user_id,
    product_code,
    @triggered_at,
    trigger_type,
    model_or_rule_version,
    @input_start_date,
    @input_end_date,
    run_status
)
SET
    triggered_at =
        STR_TO_DATE(@triggered_at, '%Y-%m-%dT%H:%i:%s'),

    input_start_date =
        CASE
            WHEN NULLIF(TRIM(@input_start_date), '') IS NULL THEN NULL
            ELSE STR_TO_DATE(
                @input_start_date,
                '%Y-%m-%dT%H:%i:%s'
            )
        END,

    input_end_date =
        CASE
            WHEN NULLIF(TRIM(@input_end_date), '') IS NULL THEN NULL
            ELSE STR_TO_DATE(
                @input_end_date,
                '%Y-%m-%dT%H:%i:%s'
            )
        END;


-- 16. INSIGHTS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/insights.csv'
INTO TABLE insights
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    insight_id,
    run_id,
    user_id,
    product_code,
    insight_type,
    insight_text,
    @severity_or_priority,
    @explanation_text,
    @generated_at
)
SET
    severity_or_priority =
        NULLIF(TRIM(@severity_or_priority), ''),

    explanation_text =
        NULLIF(TRIM(@explanation_text), ''),

    generated_at =
        STR_TO_DATE(@generated_at, '%Y-%m-%dT%H:%i:%s');




-- 17. RECOMMENDATIONS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/recommendations.csv'
INTO TABLE recommendations
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    recommendation_id,
    insight_id,
    user_id,
    product_code,
    recommendation_type,
    recommendation_text,
    @priority,
    @created_at
)
SET
    priority =
        NULLIF(TRIM(@priority), ''),

    created_at =
        STR_TO_DATE(@created_at, '%Y-%m-%dT%H:%i:%s');



-- 18. ACTIONS
-- ============================================================
LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/actions.csv'
INTO TABLE actions
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    action_id,
    recommendation_id,
    user_id,
    action_type,
    action_status,
    @action_at
)
SET
    action_at =
        STR_TO_DATE(@action_at, '%Y-%m-%dT%H:%i:%s');



-- 19. AUDIT LOGS
-- ============================================================

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense_synthetic_v1_corrected (1)/dumosense_synthetic_v1_corrected/audit_logs.csv'
INTO TABLE audit_logs
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    audit_id,
    @actor_user_id,
    action,
    resource_type,
    @resource_id,
    @audit_timestamp,
    status
)
SET
    actor_user_id =
        NULLIF(TRIM(@actor_user_id), ''),
    resource_id =
        NULLIF(TRIM(@resource_id), ''),
    timestamp =
        STR_TO_DATE(@audit_timestamp, '%Y-%m-%dT%H:%i:%s');

-- query to see whether the row counts match our synthetic dataset:
SELECT 'users' AS table_name, COUNT(*) AS rows_loaded FROM users
UNION ALL
SELECT 'assessment_types', COUNT(*) FROM assessment_types
UNION ALL
SELECT 'cognitive_tasks', COUNT(*) FROM cognitive_tasks
UNION ALL
SELECT 'user_profiles', COUNT(*) FROM user_profiles
UNION ALL
SELECT 'product_enrollments', COUNT(*) FROM product_enrollments
UNION ALL
SELECT 'consents', COUNT(*) FROM consents
UNION ALL
SELECT 'consent_history', COUNT(*) FROM consent_history
UNION ALL
SELECT 'assessment_sessions', COUNT(*) FROM assessment_sessions
UNION ALL
SELECT 'cognitive_responses', COUNT(*) FROM cognitive_responses
UNION ALL
SELECT 'cognitive_results', COUNT(*) FROM cognitive_results
UNION ALL
SELECT 'wellbeing_checkins', COUNT(*) FROM wellbeing_checkins
UNION ALL
SELECT 'context_records', COUNT(*) FROM context_records
UNION ALL
SELECT 'health_reserve_assessments', COUNT(*) FROM health_reserve_assessments
UNION ALL
SELECT 'events', COUNT(*) FROM events
UNION ALL
SELECT 'intelligence_runs', COUNT(*) FROM intelligence_runs
UNION ALL
SELECT 'insights', COUNT(*) FROM insights
UNION ALL
SELECT 'recommendations', COUNT(*) FROM recommendations
UNION ALL
SELECT 'actions', COUNT(*) FROM actions
UNION ALL
SELECT 'audit_logs', COUNT(*) FROM audit_logs;


-- ============================================================
-- DUMOSENSE REFERENTIAL INTEGRITY VALIDATION
-- Expected result for EVERY check: 0
-- ============================================================
-- 1. USER PROFILES WITHOUT VALID USERS
SELECT 'user_profiles -> users' AS integrity_check,
       COUNT(*) AS orphan_records
FROM user_profiles p
LEFT JOIN users u
    ON p.user_id = u.user_id
WHERE u.user_id IS NULL;

-- 2. PRODUCT ENROLLMENTS WITHOUT VALID USERS
SELECT 'product_enrollments -> users' AS integrity_check,
       COUNT(*) AS orphan_records
FROM product_enrollments pe
LEFT JOIN users u
    ON pe.user_id = u.user_id
WHERE u.user_id IS NULL;

-- 3. CONSENTS WITHOUT VALID USERS
SELECT 'consents -> users' AS integrity_check,
       COUNT(*) AS orphan_records
FROM consents c
LEFT JOIN users u
    ON c.user_id = u.user_id
WHERE u.user_id IS NULL;




SELECT COUNT(*) AS user_count
FROM users;

describe users;

ALTER TABLE users
    ADD COLUMN password VARCHAR(128) NULL,
    ADD COLUMN last_login DATETIME(6) NULL,
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN is_staff BOOLEAN NOT NULL DEFAULT FALSE;
    
DESCRIBE users;

SELECT
    user_id,
    first_name,
    last_name,
    email,
    account_status,
    password,
    last_login,
    is_active,
    is_staff
FROM users
LIMIT 5;

SELECT
    COUNT(*) AS total_users,
    SUM(password IS NULL) AS users_without_password,
    SUM(is_active = 1) AS active_users,
    SUM(is_staff = 1) AS staff_users
FROM users;

SET SQL_SAFE_UPDATES = 0;

UPDATE users
SET password = '!'
WHERE password IS NULL;

SET SQL_SAFE_UPDATES = 1;

SELECT
    COUNT(*) AS total_users,
    SUM(password IS NULL) AS null_passwords,
    SUM(password = '!') AS unusable_passwords
FROM users;

ALTER TABLE users
MODIFY COLUMN password VARCHAR(128) NOT NULL;

DESCRIBE users;

USE dumosense_dev;

-- ==============================================================
-- FINANCIAL HEALTH RESERVE TABLES
-- ==============================================================
-- 1. FINANCIAL PROFILES
-- Stores a user's financial profile over a defined period, including income,
-- employment status, essential expenses, debt repayments, other obligations,
-- liquid savings, income stability, currency, and location.
-- Relationships:
-- users 1 ----< financial_profiles
-- One user can have multiple financial profiles recorded over different
-- effective dates as their financial circumstances change.
CREATE TABLE financial_profiles (
  financial_profile_id VARCHAR(20) PRIMARY KEY,
  user_id VARCHAR(20) NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE NULL,
  income_type VARCHAR(30) NOT NULL,
  employment_status VARCHAR(30) NOT NULL,
  monthly_income DECIMAL(15,2) NOT NULL,
  essential_monthly_expenses DECIMAL(15,2) NOT NULL,
  debt_repayments DECIMAL(15,2) NOT NULL,
  other_monthly_obligations DECIMAL(15,2) NOT NULL,
  existing_liquid_savings DECIMAL(15,2) NOT NULL,
  income_stability_index DECIMAL(5,4) NOT NULL,
  currency_code CHAR(3) NOT NULL,
  country_code CHAR(2) NOT NULL,
  region_code VARCHAR(100) NOT NULL,
  recorded_at DATETIME NOT NULL,
  data_source VARCHAR(40) NOT NULL,
  CONSTRAINT fk_hr_fin_profile_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  UNIQUE KEY uq_hr_fin_profile_user_effective (user_id, effective_from),
  CHECK (monthly_income >= 0 AND essential_monthly_expenses >= 0 AND debt_repayments >= 0 AND other_monthly_obligations >= 0 AND existing_liquid_savings >= 0),
  CHECK (income_stability_index BETWEEN 0 AND 1)
);

-- 2. FINANCIAL TRANSACTIONS
-- Stores individual income and expense transactions associated with a user.
-- Each record captures the transaction date, type, category, amount, currency,
-- source, and whether the transaction is recurring.
-- Relationships:
-- users 1 ----< financial_transactions
-- One user can have many financial transactions.

CREATE TABLE financial_transactions (
  transaction_id VARCHAR(20) PRIMARY KEY,
  user_id VARCHAR(20) NOT NULL,
  transaction_date DATE NOT NULL,
  transaction_type VARCHAR(20) NOT NULL,
  category VARCHAR(60) NOT NULL,
  amount DECIMAL(15,2) NOT NULL,
  currency_code CHAR(3) NOT NULL,
  source_type VARCHAR(40) NOT NULL,
  is_recurring BOOLEAN NOT NULL,
  recorded_at DATETIME NOT NULL,
  CONSTRAINT fk_hr_transaction_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  INDEX idx_hr_transaction_user_date (user_id, transaction_date),
  CHECK (transaction_type IN ('income','expense')),
  CHECK (amount > 0)
);
alter table financial_transactions modify column is_recurring varchar(10) not null;


-- 3. HEALTHCARE COST REFERENCE
-- Stores reference estimates for healthcare costs across countries, regions,
-- service categories, and care settings. Each record contains low, typical,
-- and high cost estimates, currency, source information, validity dates,
-- confidence level, and data status.
-- Relationships:
-- healthcare_cost_reference is an independent reference table.
-- healthcare_cost_reference 1 ----< healthcare_exposure_items
-- One healthcare cost reference can be used by many healthcare exposure items.
CREATE TABLE healthcare_cost_reference (
  cost_reference_id VARCHAR(20) PRIMARY KEY,
  country_code CHAR(2) NOT NULL,
  region_code VARCHAR(100) NOT NULL,
  service_category VARCHAR(60) NOT NULL,
  care_setting VARCHAR(20) NOT NULL,
  estimated_cost_low DECIMAL(15,2) NOT NULL,
  estimated_cost_typical DECIMAL(15,2) NOT NULL,
  estimated_cost_high DECIMAL(15,2) NOT NULL,
  currency_code CHAR(3) NOT NULL,
  source_name VARCHAR(100) NOT NULL,
  source_date DATE NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE NULL,
  confidence_level VARCHAR(10) NOT NULL,
  data_status VARCHAR(20) NOT NULL,
  UNIQUE KEY uq_hr_cost_region_service_setting (country_code, region_code, service_category, care_setting, source_date),
  CHECK (estimated_cost_low >= 0 AND estimated_cost_low <= estimated_cost_typical AND estimated_cost_typical <= estimated_cost_high)
);

-- 4. FAMILY DEPENDENTS
-- Stores information about people financially dependent on a user, including
-- their relationship to the user, age band, level of financial dependency,
-- and the period during which the dependency record is valid.
-- Relationships:
-- users 1 ----< family_dependents
-- family_dependents 1 ----< healthcare_exposure_items
-- One user can have many dependents, and a dependent can be associated with
-- many healthcare exposure items.
CREATE TABLE family_dependents (
  dependent_id VARCHAR(20) PRIMARY KEY,
  user_id VARCHAR(20) NOT NULL,
  relationship VARCHAR(20) NOT NULL,
  age_band VARCHAR(20) NOT NULL,
  financial_dependency_level VARCHAR(10) NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE NULL,
  recorded_at DATETIME NOT NULL,
  CONSTRAINT fk_hr_dependent_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  INDEX idx_hr_dependent_user (user_id),
  CHECK (relationship IN ('child','spouse','parent','sibling','other')),
  CHECK (financial_dependency_level IN ('full','partial'))
);

-- 5. HEALTH RESERVE GOALS
-- Stores a user's Health Reserve savings goal, including the system-recommended
-- target, optional user-proposed target, selected target, target source,
-- currency, target date, and goal status. It also records the related product
-- enrollment and optional intelligence recommendation run.
-- Relationships:
-- users 1 ----< health_reserve_goals
-- product_enrollments 1 ----< health_reserve_goals
-- intelligence_runs 1 ----< health_reserve_goals
-- health_reserve_goals 1 ----< health_reserve_activity
-- health_reserve_goals 1 ----< health_reserve_scenarios
-- One user can have multiple reserve goals. Each goal belongs to one user and
-- one product enrollment, and may reference an intelligence run.

CREATE TABLE health_reserve_goals (
  goal_id VARCHAR(20) PRIMARY KEY,
  user_id VARCHAR(20) NOT NULL,
  product_enrollment_id VARCHAR(20) NOT NULL,
  recommended_target DECIMAL(15,2) NOT NULL,
  user_proposed_target DECIMAL(15,2) NULL,
  selected_target DECIMAL(15,2) NOT NULL,
  target_source VARCHAR(20) NOT NULL,
  target_currency CHAR(3) NOT NULL,
  target_date DATE NOT NULL,
  goal_status VARCHAR(20) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  recommendation_run_id VARCHAR(20) NULL,
  CONSTRAINT fk_hr_goal_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  CONSTRAINT fk_hr_goal_enrollment FOREIGN KEY (product_enrollment_id) REFERENCES product_enrollments(enrollment_id),
  CONSTRAINT fk_hr_goal_run FOREIGN KEY (recommendation_run_id) REFERENCES intelligence_runs(run_id),
  INDEX idx_hr_goal_user_status (user_id, goal_status),
  CHECK (recommended_target >= 0 AND selected_target >= 0),
  CHECK (user_proposed_target IS NULL OR user_proposed_target >= 0),
  CHECK (target_source IN ('system_recommended','user_defined'))
);

-- 6. HEALTH RESERVE ACTIVITY
-- Stores activities recorded against a Health Reserve goal, including reported
-- allocations, reported withdrawals, and balance adjustments. Each record
-- captures the activity date, amount, currency, source, and recording date.
-- Relationships:
-- health_reserve_goals 1 ----< health_reserve_activity
-- users 1 ----< health_reserve_activity
-- One reserve goal can have many activity records, and each activity record
-- is associated with one user.

CREATE TABLE health_reserve_activity (
  activity_id VARCHAR(20) PRIMARY KEY,
  goal_id VARCHAR(20) NOT NULL,
  user_id VARCHAR(20) NOT NULL,
  activity_date DATE NOT NULL,
  activity_type VARCHAR(30) NOT NULL,
  amount DECIMAL(15,2) NOT NULL,
  currency_code CHAR(3) NOT NULL,
  source_type VARCHAR(40) NOT NULL,
  recorded_at DATETIME NOT NULL,
  CONSTRAINT fk_hr_activity_goal FOREIGN KEY (goal_id) REFERENCES health_reserve_goals(goal_id),
  CONSTRAINT fk_hr_activity_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  INDEX idx_hr_activity_user_date (user_id, activity_date),
  INDEX idx_hr_activity_goal_date (goal_id, activity_date),
  CHECK (amount > 0),
  CHECK (activity_type IN ('reported_allocation','reported_withdrawal','balance_adjustment'))
);

-- 7. HEALTH RESERVE SCENARIOS
-- Stores financial stress-test scenarios associated with a user's reserve goal.
-- Scenarios can represent income reductions or unexpected healthcare costs.
-- Each record captures the scenario duration, income and expense changes,
-- assumed healthcare cost, currency, status, and scenario version.
-- Relationships:
-- users 1 ----< health_reserve_scenarios
-- health_reserve_goals 1 ----< health_reserve_scenarios
-- One user can have multiple scenarios, and one reserve goal can be evaluated
-- against multiple scenarios.
CREATE TABLE health_reserve_scenarios (
  scenario_id VARCHAR(20) PRIMARY KEY,
  user_id VARCHAR(20) NOT NULL,
  goal_id VARCHAR(20) NOT NULL,
  scenario_type VARCHAR(40) NOT NULL,
  scenario_start_date DATE NOT NULL,
  scenario_duration_months SMALLINT NOT NULL,
  income_change_pct DECIMAL(6,4) NOT NULL,
  expense_change_pct DECIMAL(6,4) NOT NULL,
  healthcare_cost_assumption DECIMAL(15,2) NOT NULL,
  currency_code CHAR(3) NOT NULL,
  scenario_status VARCHAR(20) NOT NULL,
  scenario_version VARCHAR(30) NOT NULL,
  created_at DATETIME NOT NULL,
  CONSTRAINT fk_hr_scenario_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  CONSTRAINT fk_hr_scenario_goal FOREIGN KEY (goal_id) REFERENCES health_reserve_goals(goal_id),
  CHECK (scenario_duration_months > 0 AND healthcare_cost_assumption >= 0),
  CHECK (scenario_type IN ('income_reduction','unexpected_healthcare_cost'))
);

-- 8. HEALTHCARE EXPOSURE ITEMS
-- Stores estimated healthcare expenses associated with a user's existing
-- Health Reserve assessment. Each record identifies the healthcare service,
-- quantity, estimated amount, currency, cost reference, and optional dependent.
-- Relationships:
-- health_reserve_assessments 1 ----< healthcare_exposure_items
-- users 1 ----< healthcare_exposure_items
-- healthcare_cost_reference 1 ----< healthcare_exposure_items
-- family_dependents 1 ----< healthcare_exposure_items
-- One assessment can contain many healthcare exposure items. Each exposure
-- item belongs to one user, references one healthcare cost record, and may
-- optionally be associated with a dependent.
CREATE TABLE healthcare_exposure_items (
  exposure_item_id VARCHAR(20) PRIMARY KEY,
  reserve_assessment_id VARCHAR(20) NOT NULL,
  user_id VARCHAR(20) NOT NULL,
  cost_reference_id VARCHAR(20) NOT NULL,
  dependent_id VARCHAR(20) NULL,
  service_category VARCHAR(60) NOT NULL,
  quantity DECIMAL(8,2) NOT NULL,
  estimated_amount DECIMAL(15,2) NOT NULL,
  currency_code CHAR(3) NOT NULL,
  assumption_source VARCHAR(50) NOT NULL,
  created_at DATETIME NOT NULL,
  CONSTRAINT fk_hr_exposure_assessment FOREIGN KEY (reserve_assessment_id) REFERENCES health_reserve_assessments(reserve_assessment_id),
  CONSTRAINT fk_hr_exposure_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  CONSTRAINT fk_hr_exposure_cost FOREIGN KEY (cost_reference_id) REFERENCES healthcare_cost_reference(cost_reference_id),
  CONSTRAINT fk_hr_exposure_dependent FOREIGN KEY (dependent_id) REFERENCES family_dependents(dependent_id),
  INDEX idx_hr_exposure_assessment (reserve_assessment_id),
  CHECK (quantity > 0 AND estimated_amount >= 0)
);

-- 9. HEALTH RESERVE CONTRIBUTION PLANS
-- Stores estimated contribution capacity, system suggestions,
-- and user-selected monthly Health Reserve contributions.
-- Relationships:
-- users 1 ----< health_reserve_contribution_plans
-- health_reserve_goals 1 ----< health_reserve_contribution_plans
-- financial_profiles 1 ----< health_reserve_contribution_plans
-- One user can have multiple plans. Each plan references
-- one goal and one financial profile.

-- 9. HEALTH RESERVE CONTRIBUTION PLANS
-- Stores estimated contribution capacity, system suggestions,
-- and user-selected monthly Health Reserve contributions.
-- Relationships:
-- users 1 ----< health_reserve_contribution_plans
-- health_reserve_goals 1 ----< health_reserve_contribution_plans
-- financial_profiles 1 ----< health_reserve_contribution_plans
-- One user can have multiple plans. Each plan references
-- one goal and one financial profile.

CREATE TABLE IF NOT EXISTS health_reserve_contribution_plans (
    plan_id VARCHAR(20) PRIMARY KEY,
    goal_id VARCHAR(20) NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    financial_profile_id VARCHAR(20) NOT NULL,
    choice_timestamp DATETIME NOT NULL,
    estimated_monthly_surplus DECIMAL(15,2) NOT NULL,
    rule_based_capacity_estimate DECIMAL(15,2) NOT NULL,
    system_suggested_monthly_contribution DECIMAL(15,2) NOT NULL,
    user_selected_monthly_contribution DECIMAL(15,2) NULL,
    contribution_currency CHAR(3) NOT NULL,
    choice_status VARCHAR(20) NOT NULL,
    plan_frequency VARCHAR(20) NOT NULL,
    cashflow_coverage VARCHAR(30) NOT NULL,
    data_source VARCHAR(40) NOT NULL,
    plan_status VARCHAR(30) NOT NULL,
    created_at DATETIME NOT NULL,

    CONSTRAINT fk_hrcp_goal
        FOREIGN KEY (goal_id)
        REFERENCES health_reserve_goals(goal_id),

    CONSTRAINT fk_hrcp_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    CONSTRAINT fk_hrcp_profile
        FOREIGN KEY (financial_profile_id)
        REFERENCES financial_profiles(financial_profile_id),

    CONSTRAINT chk_hrcp_choice
        CHECK (
            user_selected_monthly_contribution IS NULL
            OR user_selected_monthly_contribution >= 0
        ),

    CONSTRAINT chk_hrcp_status
        CHECK (
            (choice_status = 'undecided'
             AND user_selected_monthly_contribution IS NULL)
            OR
            (choice_status = 'zero_for_now'
             AND user_selected_monthly_contribution = 0)
            OR
            (choice_status = 'selected'
             AND user_selected_monthly_contribution > 0)
        )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. HEALTH RESERVE AFFORDABILITY OUTCOMES
-- Stores monthly contribution outcomes, financial strain,
-- and sustainability feedback for each contribution plan.
-- Relationships:
-- health_reserve_contribution_plans 1 ----< health_reserve_affordability_outcomes
-- users 1 ----< health_reserve_affordability_outcomes
-- One plan can have multiple outcomes across review periods.
-- Each outcome belongs to one plan and one user.

CREATE TABLE IF NOT EXISTS health_reserve_affordability_outcomes (
    outcome_id VARCHAR(20) PRIMARY KEY,
    plan_id VARCHAR(20) NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    review_period_start DATE NOT NULL,
    review_period_end DATE NOT NULL,
    expected_contribution DECIMAL(15,2) NOT NULL,
    reported_contribution DECIMAL(15,2) NULL,
    contribution_currency CHAR(3) NOT NULL,
    reported_financial_strain VARCHAR(10) NOT NULL,
    sustainability_status VARCHAR(25) NOT NULL,
    adjustment_reason VARCHAR(50) NOT NULL,
    observation_status VARCHAR(20) NOT NULL,
    data_source VARCHAR(40) NOT NULL,
    recorded_at DATETIME NOT NULL,

    CONSTRAINT fk_hrco_plan
        FOREIGN KEY (plan_id)
        REFERENCES health_reserve_contribution_plans(plan_id),

    CONSTRAINT fk_hrco_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    CONSTRAINT uq_hrco_period
        UNIQUE (plan_id, review_period_start),

    CONSTRAINT chk_hrco_period
        CHECK (review_period_end > review_period_start),

    CONSTRAINT chk_hrco_amount
        CHECK (
            expected_contribution >= 0
            AND (
                reported_contribution IS NULL
                OR reported_contribution >= 0
            )
        )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SHOW TABLES LIKE 'health_reserve_contribution_plans';

SHOW TABLES LIKE 'financial_profiles';
SHOW TABLES LIKE 'financial_transactions';
SHOW TABLES LIKE 'healthcare_cost_reference';
SHOW TABLES LIKE 'family_dependents';
SHOW TABLES LIKE 'health_reserve_goals';
SHOW TABLES LIKE 'health_reserve_activity';
SHOW TABLES LIKE 'health_reserve_scenarios';
SHOW TABLES LIKE 'healthcare_exposure_items';

SET GLOBAL local_infile = 1;

SHOW GLOBAL VARIABLES LIKE 'local_infile';

LOAD DATA LOCAL INFILE
'C:\\Users\\TBelema\\Downloads\\dumosense\\dumosense_health_reserve_extension\\financial_profiles.csv'
INTO TABLE financial_profiles
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    financial_profile_id,
    user_id,
    effective_from,
    @effective_to,
    income_type,
    employment_status,
    monthly_income,
    essential_monthly_expenses,
    debt_repayments,
    other_monthly_obligations,
    existing_liquid_savings,
    income_stability_index,
    currency_code,
    country_code,
    region_code,
    @recorded_at,
    data_source
)
SET
    effective_to = NULLIF(@effective_to, ''),
    recorded_at = STR_TO_DATE(@recorded_at, '%Y-%m-%dT%H:%i:%s');

USE dumosense_dev;

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense/dumosense_health_reserve_extension/healthcare_cost_reference.csv'
INTO TABLE healthcare_cost_reference
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    cost_reference_id,
    country_code,
    region_code,
    service_category,
    care_setting,
    estimated_cost_low,
    estimated_cost_typical,
    estimated_cost_high,
    currency_code,
    source_name,
    source_date,
    valid_from,
    @valid_to,
    confidence_level,
    data_status
)
SET valid_to = NULLIF(@valid_to, '');

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense/dumosense_health_reserve_extension/family_dependents.csv'
INTO TABLE family_dependents
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    dependent_id,
    user_id,
    relationship,
    age_band,
    financial_dependency_level,
    effective_from,
    @effective_to,
    @recorded_at
)
SET
    effective_to = NULLIF(@effective_to, ''),
    recorded_at = STR_TO_DATE(@recorded_at, '%Y-%m-%dT%H:%i:%s');
    
LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense/dumosense_health_reserve_extension/financial_transactions.csv'
INTO TABLE financial_transactions
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    transaction_id,
    user_id,
    transaction_date,
    transaction_type,
    category,
    amount,
    currency_code,
    source_type,
    is_recurring,
    @recorded_at
)
SET recorded_at = STR_TO_DATE(@recorded_at, '%Y-%m-%dT%H:%i:%s');

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense/dumosense_health_reserve_extension/health_reserve_goals.csv'
INTO TABLE health_reserve_goals
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    goal_id,
    user_id,
    product_enrollment_id,
    recommended_target,
    @user_proposed_target,
    selected_target,
    target_source,
    target_currency,
    target_date,
    goal_status,
    @created_at,
    @updated_at,
    @recommendation_run_id
)
SET
    user_proposed_target = NULLIF(@user_proposed_target, ''),
    created_at = STR_TO_DATE(@created_at, '%Y-%m-%dT%H:%i:%s'),
    updated_at = STR_TO_DATE(@updated_at, '%Y-%m-%dT%H:%i:%s'),
    recommendation_run_id = NULLIF(@recommendation_run_id, '');

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense/dumosense_health_reserve_extension/health_reserve_activity.csv'
INTO TABLE health_reserve_activity
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    activity_id,
    goal_id,
    user_id,
    activity_date,
    activity_type,
    amount,
    currency_code,
    source_type,
    @recorded_at
)
SET recorded_at = STR_TO_DATE(@recorded_at, '%Y-%m-%dT%H:%i:%s');

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense/dumosense_health_reserve_extension/health_reserve_scenarios.csv'
INTO TABLE health_reserve_scenarios
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    scenario_id,
    user_id,
    goal_id,
    scenario_type,
    scenario_start_date,
    scenario_duration_months,
    income_change_pct,
    expense_change_pct,
    healthcare_cost_assumption,
    currency_code,
    scenario_status,
    scenario_version,
    @created_at
)
SET created_at = STR_TO_DATE(@created_at, '%Y-%m-%dT%H:%i:%s');

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense/dumosense_health_reserve_extension/healthcare_exposure_items.csv'
INTO TABLE healthcare_exposure_items
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    exposure_item_id,
    reserve_assessment_id,
    user_id,
    cost_reference_id,
    @dependent_id,
    service_category,
    quantity,
    estimated_amount,
    currency_code,
    assumption_source,
    @created_at
)
SET
    dependent_id = NULLIF(@dependent_id, ''),
    created_at = STR_TO_DATE(@created_at, '%Y-%m-%d %H:%i:%s');
    
LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense/dumosense_health_reserve_extension/health_reserve_contribution_plans.csv'
INTO TABLE health_reserve_contribution_plans
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    plan_id,
    goal_id,
    user_id,
    financial_profile_id,
    @choice_timestamp,
    estimated_monthly_surplus,
    rule_based_capacity_estimate,
    system_suggested_monthly_contribution,
    @user_selected_monthly_contribution,
    contribution_currency,
    choice_status,
    plan_frequency,
    cashflow_coverage,
    data_source,
    plan_status,
    @created_at
)
SET
    choice_timestamp = STR_TO_DATE(
        REPLACE(@choice_timestamp, 'T', ' '),
        '%Y-%m-%d %H:%i:%s'
    ),
    user_selected_monthly_contribution =
        CASE
            WHEN TRIM(@user_selected_monthly_contribution) = ''
                THEN NULL
            ELSE @user_selected_monthly_contribution
        END,
    created_at = STR_TO_DATE(
        REPLACE(@created_at, 'T', ' '),
        '%Y-%m-%d %H:%i:%s'
    );
    
LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense/dumosense_health_reserve_extension/health_reserve_affordability_outcomes.csv'
INTO TABLE health_reserve_affordability_outcomes
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    outcome_id,
    plan_id,
    user_id,
    review_period_start,
    review_period_end,
    expected_contribution,
    @reported_contribution,
    contribution_currency,
    reported_financial_strain,
    sustainability_status,
    adjustment_reason,
    observation_status,
    data_source,
    @recorded_at
)
SET
    reported_contribution =
        CASE
            WHEN TRIM(@reported_contribution) = ''
                THEN NULL
            ELSE @reported_contribution
        END,
    recorded_at = STR_TO_DATE(
        REPLACE(@recorded_at, 'T', ' '),
        '%Y-%m-%d %H:%i:%s'
    );

SELECT 'financial_profiles' AS table_name, COUNT(*) AS records FROM financial_profiles
UNION ALL
SELECT 'healthcare_cost_reference', COUNT(*) FROM healthcare_cost_reference
UNION ALL
SELECT 'family_dependents', COUNT(*) FROM family_dependents
UNION ALL
SELECT 'financial_transactions', COUNT(*) FROM financial_transactions
UNION ALL
SELECT 'health_reserve_goals', COUNT(*) FROM health_reserve_goals
UNION ALL
SELECT 'health_reserve_activity', COUNT(*) FROM health_reserve_activity
UNION ALL
SELECT 'health_reserve_scenarios', COUNT(*) FROM health_reserve_scenarios
UNION ALL
SELECT 'healthcare_exposure_items', COUNT(*) FROM healthcare_exposure_items;

SELECT
    COUNT(*) AS total_records,
    COUNT(DISTINCT transaction_id) AS unique_transactions,
    COUNT(*) - COUNT(DISTINCT transaction_id) AS duplicate_ids
FROM financial_transactions;

SELECT is_recurring, COUNT(*) AS records
FROM financial_transactions
GROUP BY is_recurring;


-- every orphan_records value should be 0.
-- checking for orphan records, used to check relationship.

SELECT 'financial_profiles → users' AS relationship,
       COUNT(*) AS orphan_records
FROM financial_profiles f
LEFT JOIN users u ON f.user_id = u.user_id
WHERE u.user_id IS NULL

UNION ALL

SELECT 'financial_transactions → users',
       COUNT(*)
FROM financial_transactions t
LEFT JOIN users u ON t.user_id = u.user_id
WHERE u.user_id IS NULL

UNION ALL

SELECT 'family_dependents → users',
       COUNT(*)
FROM family_dependents d
LEFT JOIN users u ON d.user_id = u.user_id
WHERE u.user_id IS NULL

UNION ALL

SELECT 'health_reserve_goals → users',
       COUNT(*)
FROM health_reserve_goals g
LEFT JOIN users u ON g.user_id = u.user_id
WHERE u.user_id IS NULL

UNION ALL

SELECT 'health_reserve_activity → goals',
       COUNT(*)
FROM health_reserve_activity a
LEFT JOIN health_reserve_goals g ON a.goal_id = g.goal_id
WHERE g.goal_id IS NULL

UNION ALL

SELECT 'health_reserve_scenarios → goals',
       COUNT(*)
FROM health_reserve_scenarios s
LEFT JOIN health_reserve_goals g ON s.goal_id = g.goal_id
WHERE g.goal_id IS NULL

UNION ALL

SELECT 'healthcare_exposure_items → assessments',
       COUNT(*)
FROM healthcare_exposure_items e
LEFT JOIN health_reserve_assessments a
    ON e.reserve_assessment_id = a.reserve_assessment_id
WHERE a.reserve_assessment_id IS NULL

UNION ALL

SELECT 'healthcare_exposure_items → cost reference',
       COUNT(*)
FROM healthcare_exposure_items e
LEFT JOIN healthcare_cost_reference c
    ON e.cost_reference_id = c.cost_reference_id
WHERE c.cost_reference_id IS NULL;

-- testing ownership consistency
-- There is another important check. 
-- A record might reference an existing goal but belong to a different user. 
-- Ordinary foreign keys don't necessarily prevent that.

SELECT 'Activity user vs goal owner' AS validation,
       COUNT(*) AS mismatches
FROM health_reserve_activity a
JOIN health_reserve_goals g ON a.goal_id = g.goal_id
WHERE a.user_id <> g.user_id

UNION ALL

SELECT 'Scenario user vs goal owner',
       COUNT(*)
FROM health_reserve_scenarios s
JOIN health_reserve_goals g ON s.goal_id = g.goal_id
WHERE s.user_id <> g.user_id

UNION ALL

SELECT 'Exposure user vs assessment owner',
       COUNT(*)
FROM healthcare_exposure_items e
JOIN health_reserve_assessments a
    ON e.reserve_assessment_id = a.reserve_assessment_id
WHERE e.user_id <> a.user_id

UNION ALL

SELECT 'Exposure dependent vs user',
       COUNT(*)
FROM healthcare_exposure_items e
JOIN family_dependents d ON e.dependent_id = d.dependent_id
WHERE e.user_id <> d.user_id;

select * from financial_transactions;

SHOW CREATE TABLE financial_transactions;

SELECT *
FROM financial_transactions
LIMIT 5;

USE dumosense_dev;

CREATE TABLE financial_transactions_backup AS
SELECT *
FROM financial_transactions;

SELECT COUNT(*) AS backup_records
FROM financial_transactions_backup;

TRUNCATE TABLE financial_transactions;

DESCRIBE financial_transactions;

LOAD DATA LOCAL INFILE
'C:/Users/TBelema/Downloads/dumosense/dumosense_health_reserve_extension/financial_transactions.csv'
INTO TABLE financial_transactions
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(
    transaction_id,
    user_id,
    transaction_date,
    transaction_type,
    category,
    amount,
    currency_code,
    source_type,
    @is_recurring,
    recorded_at
)
SET is_recurring =
    CASE
        WHEN LOWER(TRIM(@is_recurring)) = 'true' THEN '1'
        WHEN LOWER(TRIM(@is_recurring)) = 'false' THEN '0'
        ELSE NULL
    END;
    
    SELECT
    is_recurring,
    COUNT(*) AS record_count
FROM financial_transactions
GROUP BY is_recurring
ORDER BY is_recurring;

SELECT COUNT(*) AS total_records
FROM financial_transactions;

SELECT
    TABLE_NAME,
    ORDINAL_POSITION,
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_KEY,
    COLUMN_DEFAULT,
    EXTRA
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'dumosense_dev'
  AND TABLE_NAME IN (
      'financial_profiles',
      'financial_transactions',
      'healthcare_cost_reference',
      'family_dependents',
      'health_reserve_goals',
      'health_reserve_activity',
      'health_reserve_scenarios',
      'healthcare_exposure_items'
  )
ORDER BY TABLE_NAME, ORDINAL_POSITION;


SELECT
    TABLE_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME,
    CONSTRAINT_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'dumosense_dev'
  AND TABLE_NAME IN (
      'financial_profiles',
      'financial_transactions',
      'healthcare_cost_reference',
      'family_dependents',
      'health_reserve_goals',
      'health_reserve_activity',
      'health_reserve_scenarios',
      'healthcare_exposure_items'
  )
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, COLUMN_NAME;

SELECT
    'Contribution Plans' AS table_name,
    COUNT(*) AS total_records
FROM health_reserve_contribution_plans

UNION ALL

SELECT
    'Affordability Outcomes',
    COUNT(*)
FROM health_reserve_affordability_outcomes;


SELECT 'Plan vs Goal' AS validation,
       COUNT(*) AS mismatches
FROM health_reserve_contribution_plans p
JOIN health_reserve_goals g
    ON p.goal_id = g.goal_id
WHERE p.user_id <> g.user_id

UNION ALL

SELECT 'Plan vs Financial Profile',
       COUNT(*)
FROM health_reserve_contribution_plans p
JOIN financial_profiles f
    ON p.financial_profile_id = f.financial_profile_id
WHERE p.user_id <> f.user_id

UNION ALL

SELECT 'Outcome vs Plan',
       COUNT(*)
FROM health_reserve_affordability_outcomes o
JOIN health_reserve_contribution_plans p
    ON o.plan_id = p.plan_id
WHERE o.user_id <> p.user_id;


SELECT
    sustainability_status,
    observation_status,
    reported_financial_strain,
    COUNT(*) AS total_records,
    ROUND(AVG(expected_contribution), 2) AS avg_expected,
    ROUND(AVG(reported_contribution), 2) AS avg_reported
FROM health_reserve_affordability_outcomes
GROUP BY
    sustainability_status,
    observation_status,
    reported_financial_strain
ORDER BY total_records DESC;

SELECT
    sustainability_status,
    COUNT(*) AS total_records,
    SUM(
        CASE
            WHEN reported_contribution > expected_contribution
            THEN 1 ELSE 0
        END
    ) AS above_expected,
    SUM(
        CASE
            WHEN reported_contribution = expected_contribution
            THEN 1 ELSE 0
        END
    ) AS exactly_expected,
    SUM(
        CASE
            WHEN reported_contribution < expected_contribution
            THEN 1 ELSE 0
        END
    ) AS below_expected,
    SUM(
        CASE
            WHEN reported_contribution IS NULL
            THEN 1 ELSE 0
        END
    ) AS missing_contribution
FROM health_reserve_affordability_outcomes
GROUP BY sustainability_status;

SELECT
    sustainability_status,
    COUNT(*) AS total_records,
    ROUND(
        AVG(
            CASE
                WHEN expected_contribution > 0
                THEN reported_contribution / expected_contribution
            END
        ), 3
    ) AS avg_completion_ratio,
    ROUND(
        MIN(
            CASE
                WHEN expected_contribution > 0
                THEN reported_contribution / expected_contribution
            END
        ), 3
    ) AS min_completion_ratio,
    ROUND(
        MAX(
            CASE
                WHEN expected_contribution > 0
                THEN reported_contribution / expected_contribution
            END
        ), 3
    ) AS max_completion_ratio
FROM health_reserve_affordability_outcomes
GROUP BY sustainability_status;

SELECT
    plan_id,
    COUNT(*) AS review_periods,
    SUM(sustainability_status = 'sustainable') AS sustainable_months,
    SUM(sustainability_status = 'adjusted_down') AS adjusted_months,
    SUM(sustainability_status = 'unknown') AS unknown_months
FROM health_reserve_affordability_outcomes
GROUP BY plan_id
ORDER BY adjusted_months DESC, unknown_months DESC
LIMIT 20;

SELECT
    sustainable_months,
    adjusted_months,
    unknown_months,
    COUNT(*) AS total_plans
FROM (
    SELECT
        plan_id,
        SUM(sustainability_status = 'sustainable')
            AS sustainable_months,
        SUM(sustainability_status = 'adjusted_down')
            AS adjusted_months,
        SUM(sustainability_status = 'unknown')
            AS unknown_months
    FROM health_reserve_affordability_outcomes
    GROUP BY plan_id
) AS plan_summary
GROUP BY
    sustainable_months,
    adjusted_months,
    unknown_months
ORDER BY total_plans DESC;

SELECT
    'Plan before goal creation' AS validation,
    COUNT(*) AS affected_records
FROM health_reserve_contribution_plans p
JOIN health_reserve_goals g
    ON p.goal_id = g.goal_id
WHERE p.choice_timestamp < g.created_at

UNION ALL

SELECT
    'Plan outside financial profile period',
    COUNT(*)
FROM health_reserve_contribution_plans p
JOIN financial_profiles f
    ON p.financial_profile_id = f.financial_profile_id
WHERE DATE(p.choice_timestamp) < f.effective_from
   OR (
       f.effective_to IS NOT NULL
       AND DATE(p.choice_timestamp) > f.effective_to
   )

UNION ALL

SELECT
    'Outcome before contribution choice',
    COUNT(*)
FROM health_reserve_affordability_outcomes o
JOIN health_reserve_contribution_plans p
    ON o.plan_id = p.plan_id
WHERE o.review_period_start < DATE(p.choice_timestamp)

UNION ALL

SELECT
    'Outcome recorded before review period ended',
    COUNT(*)
FROM health_reserve_affordability_outcomes
WHERE DATE(recorded_at) < review_period_end;

SELECT
    'Plan vs Goal Currency' AS validation,
    COUNT(*) AS issues
FROM health_reserve_contribution_plans p
JOIN health_reserve_goals g
    ON p.goal_id = g.goal_id
WHERE p.contribution_currency <> g.target_currency

UNION ALL

SELECT
    'Plan vs Financial Profile Currency',
    COUNT(*)
FROM health_reserve_contribution_plans p
JOIN financial_profiles f
    ON p.financial_profile_id = f.financial_profile_id
WHERE p.contribution_currency <> f.currency_code

UNION ALL

SELECT
    'Outcome vs Plan Currency',
    COUNT(*)
FROM health_reserve_affordability_outcomes o
JOIN health_reserve_contribution_plans p
    ON o.plan_id = p.plan_id
WHERE o.contribution_currency <> p.contribution_currency

UNION ALL

SELECT
    'Negative Contribution Amounts',
    COUNT(*)
FROM health_reserve_contribution_plans
WHERE estimated_monthly_surplus < 0
   OR rule_based_capacity_estimate < 0
   OR system_suggested_monthly_contribution < 0
   OR user_selected_monthly_contribution < 0;
   
SELECT
    plan_id,
    user_id,
    estimated_monthly_surplus,
    rule_based_capacity_estimate,
    system_suggested_monthly_contribution,
    user_selected_monthly_contribution,
    choice_status
FROM health_reserve_contribution_plans
WHERE estimated_monthly_surplus < 0
   OR rule_based_capacity_estimate < 0
   OR system_suggested_monthly_contribution < 0
   OR user_selected_monthly_contribution < 0;
   
SELECT
    choice_status,
    plan_status,
    COUNT(*) AS total_plans,
    ROUND(AVG(estimated_monthly_surplus), 2) AS avg_monthly_surplus,
    ROUND(AVG(rule_based_capacity_estimate), 2) AS avg_capacity,
    ROUND(AVG(system_suggested_monthly_contribution), 2) AS avg_suggested,
    ROUND(AVG(user_selected_monthly_contribution), 2) AS avg_selected
FROM health_reserve_contribution_plans
GROUP BY choice_status, plan_status
ORDER BY choice_status, plan_status;

-- VALIDATE CONTRIBUTION CHOICE RULES

SELECT
    'Selected contribution mismatch' AS validation,
    COUNT(*) AS issues
FROM health_reserve_contribution_plans
WHERE choice_status = 'selected'
  AND (
      user_selected_monthly_contribution IS NULL
      OR user_selected_monthly_contribution <= 0
  )

UNION ALL

SELECT
    'Undecided contribution mismatch',
    COUNT(*)
FROM health_reserve_contribution_plans
WHERE choice_status = 'undecided'
  AND user_selected_monthly_contribution IS NOT NULL

UNION ALL

SELECT
    'Zero-for-now contribution mismatch',
    COUNT(*)
FROM health_reserve_contribution_plans
WHERE choice_status = 'zero_for_now'
  AND (
      user_selected_monthly_contribution IS NULL
      OR user_selected_monthly_contribution <> 0
  )

UNION ALL

SELECT
    'Negative system contribution estimate',
    COUNT(*)
FROM health_reserve_contribution_plans
WHERE rule_based_capacity_estimate < 0
   OR system_suggested_monthly_contribution < 0

UNION ALL

SELECT
    'Unrecognized choice status',
    COUNT(*)
FROM health_reserve_contribution_plans
WHERE choice_status NOT IN (
    'selected',
    'undecided',
    'zero_for_now'
);


-- VALIDATE AFFORDABILITY OUTCOME RECORDS

SELECT
    'Missing reported amount for observed outcome' AS validation,
    COUNT(*) AS issues
FROM health_reserve_affordability_outcomes
WHERE observation_status = 'simulated'
  AND reported_contribution IS NULL

UNION ALL

SELECT
    'Reported amount for unobserved outcome',
    COUNT(*)
FROM health_reserve_affordability_outcomes
WHERE observation_status = 'not_observed'
  AND reported_contribution IS NOT NULL

UNION ALL

SELECT
    'Unobserved outcome classified as known',
    COUNT(*)
FROM health_reserve_affordability_outcomes
WHERE observation_status = 'not_observed'
  AND sustainability_status <> 'unknown'

UNION ALL

SELECT
    'Invalid sustainability status',
    COUNT(*)
FROM health_reserve_affordability_outcomes
WHERE sustainability_status NOT IN (
    'sustainable',
    'adjusted_down',
    'unknown'
)

UNION ALL

SELECT
    'Negative contribution amount',
    COUNT(*)
FROM health_reserve_affordability_outcomes
WHERE expected_contribution < 0
   OR reported_contribution < 0

UNION ALL

SELECT
    'Duplicate plan review periods',
    COUNT(*)
FROM (
    SELECT plan_id, review_period_start
    FROM health_reserve_affordability_outcomes
    GROUP BY plan_id, review_period_start
    HAVING COUNT(*) > 1
) AS duplicates;

-- INVESTIGATE PRE-GOAL HEALTH RESERVE ACTIVITY

SELECT
    a.goal_id,
    a.activity_id,
    a.activity_type,
    a.activity_timestamp,
    g.created_at AS goal_created_at,
    TIMESTAMPDIFF(
        DAY,
        a.activity_timestamp,
        g.created_at
    ) AS days_before_goal
FROM health_reserve_activity a
JOIN health_reserve_goals g
    ON a.goal_id = g.goal_id
WHERE a.activity_timestamp < g.created_at
ORDER BY days_before_goal DESC
LIMIT 20;

DESCRIBE health_reserve_activity;

-- INVESTIGATE ACTIVITY BEFORE GOAL CREATION

SELECT
    a.goal_id,
    a.activity_id,
    a.activity_type,
    a.source_type,
    a.amount,
    a.activity_date,
    a.recorded_at,
    g.created_at AS goal_created_at,
    DATEDIFF(
        DATE(g.created_at),
        a.activity_date
    ) AS days_before_goal
FROM health_reserve_activity a
JOIN health_reserve_goals g
    ON a.goal_id = g.goal_id
WHERE a.activity_date < DATE(g.created_at)
ORDER BY days_before_goal DESC
LIMIT 20;

-- DISTRIBUTION OF PRE-GOAL SAVINGS ACTIVITY

SELECT
    a.activity_type,
    a.source_type,
    COUNT(*) AS affected_records,
    COUNT(DISTINCT a.goal_id) AS affected_goals,
    ROUND(SUM(a.amount), 2) AS total_amount,
    MIN(DATEDIFF(DATE(g.created_at), a.activity_date))
        AS minimum_days_before_goal,
    MAX(DATEDIFF(DATE(g.created_at), a.activity_date))
        AS maximum_days_before_goal
FROM health_reserve_activity a
JOIN health_reserve_goals g
    ON a.goal_id = g.goal_id
WHERE a.activity_date < DATE(g.created_at)
GROUP BY
    a.activity_type,
    a.source_type
ORDER BY affected_records DESC;

-- CHECK HISTORICAL ALLOCATION RECORDING TIMESTAMPS

SELECT
    CASE
        WHEN a.activity_date < DATE(g.created_at)
            THEN 'pre_goal_activity'
        ELSE 'post_goal_activity'
    END AS activity_period,

    COUNT(*) AS total_records,

    SUM(a.recorded_at < g.created_at)
        AS recorded_before_goal,

    SUM(a.recorded_at >= g.created_at)
        AS recorded_after_goal

FROM health_reserve_activity a
JOIN health_reserve_goals g
    ON a.goal_id = g.goal_id

WHERE a.activity_type = 'reported_allocation'

GROUP BY activity_period;

-- BACKUP HEALTH RESERVE ACTIVITY BEFORE CORRECTION

CREATE TABLE health_reserve_activity_backup_20261105
LIKE health_reserve_activity;

INSERT INTO health_reserve_activity_backup_20261105
SELECT *
FROM health_reserve_activity;

SELECT
    COUNT(*) AS backup_records
FROM health_reserve_activity_backup_20261105;

-- CORRECT HISTORICAL ALLOCATION RECORDING TIMESTAMPS

START TRANSACTION;

UPDATE health_reserve_activity a
JOIN health_reserve_goals g
    ON a.goal_id = g.goal_id
SET a.recorded_at = DATE_ADD(
    g.created_at,
    INTERVAL 1 MINUTE
)
WHERE a.activity_type = 'reported_allocation'
  AND a.source_type = 'synthetic_user_report'
  AND a.activity_date < DATE(g.created_at)
  AND a.recorded_at < g.created_at;

SELECT ROW_COUNT() AS corrected_records;


-- VERIFY HISTORICAL ACTIVITY CORRECTION

SELECT
    COUNT(*) AS remaining_invalid_records
FROM health_reserve_activity a
JOIN health_reserve_goals g
    ON a.goal_id = g.goal_id
WHERE a.activity_type = 'reported_allocation'
  AND a.source_type = 'synthetic_user_report'
  AND a.activity_date < DATE(g.created_at)
  AND a.recorded_at < g.created_at;
SET SQL_SAFE_UPDATES = 0;

SET SQL_SAFE_UPDATES = 1;

COMMIT;

-- VERIFY CORRECTION AGAINST ORIGINAL BACKUP

SELECT
    COUNT(*) AS total_records,
    SUM(a.activity_date <> b.activity_date) AS changed_activity_dates,
    SUM(a.amount <> b.amount) AS changed_amounts,
    SUM(a.recorded_at <> b.recorded_at) AS changed_recording_timestamps
FROM health_reserve_activity a
JOIN health_reserve_activity_backup_20261105 b
    ON a.activity_id = b.activity_id;
    
-- HEALTH RESERVE EXTENSION: FINAL TABLE INVENTORY

SELECT
    table_name,
    table_rows
FROM information_schema.tables
WHERE table_schema = 'dumosense_dev'
  AND table_name IN (
      'financial_profiles',
      'financial_transactions',
      'healthcare_cost_reference',
      'family_dependents',
      'health_reserve_goals',
      'health_reserve_activity',
      'health_reserve_scenarios',
      'healthcare_exposure_items',
      'health_reserve_contribution_plans',
      'health_reserve_affordability_outcomes'
  )
ORDER BY table_name;

-- EXACT RECORD COUNTS FOR ALL 10 EXTENSION TABLES

SELECT 'financial_profiles' AS table_name, COUNT(*) AS total_records
FROM financial_profiles

UNION ALL
SELECT 'financial_transactions', COUNT(*)
FROM financial_transactions

UNION ALL
SELECT 'healthcare_cost_reference', COUNT(*)
FROM healthcare_cost_reference

UNION ALL
SELECT 'family_dependents', COUNT(*)
FROM family_dependents

UNION ALL
SELECT 'health_reserve_goals', COUNT(*)
FROM health_reserve_goals

UNION ALL
SELECT 'health_reserve_activity', COUNT(*)
FROM health_reserve_activity

UNION ALL
SELECT 'health_reserve_scenarios', COUNT(*)
FROM health_reserve_scenarios

UNION ALL
SELECT 'healthcare_exposure_items', COUNT(*)
FROM healthcare_exposure_items

UNION ALL
SELECT 'health_reserve_contribution_plans', COUNT(*)
FROM health_reserve_contribution_plans

UNION ALL
SELECT 'health_reserve_affordability_outcomes', COUNT(*)
FROM health_reserve_affordability_outcomes;