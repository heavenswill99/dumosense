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
