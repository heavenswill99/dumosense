-- DumoSense MindGuard schema deployment (Aiven development database)
-- Review before execution. Requires existing users table with compatible utf8mb4_0900_ai_ci collation.
-- Does not create databases, delete rows, or import synthetic data.
-- MySQL DDL commits independently; take a backup before applying.
-- If a table already exists, inspect its structure rather than skipping or overwriting it.

-- assessment_types
CREATE TABLE `assessment_types` (
    assessment_type_id VARCHAR(20) PRIMARY KEY,
    assessment_name VARCHAR(100) NOT NULL,
    cognitive_domain VARCHAR(50) NOT NULL,
    description VARCHAR(500),
    active INT NOT NULL DEFAULT TRUE,
    INDEX idx_assessment_domain (cognitive_domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- consents
CREATE TABLE `consents` (
    consent_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    consent_type VARCHAR(100) NOT NULL,
    purpose VARCHAR(255) NOT NULL,
    consent_version DECIMAL(5,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    granted_at DATETIME(6) NOT NULL,
    withdrawn_at DATETIME(6) NULL,
    CONSTRAINT fk_consent_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),
    INDEX idx_consent_user (user_id),
    INDEX idx_consent_type (consent_type),
    INDEX idx_consent_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- consent_history
CREATE TABLE `consent_history` (
    consent_history_id VARCHAR(20) PRIMARY KEY,
    consent_id VARCHAR(20) NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    previous_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_at DATETIME(6) NOT NULL,
    reason VARCHAR(255),
    CONSTRAINT fk_consent_history_consent
        FOREIGN KEY (consent_id)
        REFERENCES consents(consent_id),
    CONSTRAINT fk_consent_history_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),
    INDEX idx_consent_history_consent (consent_id),
    INDEX idx_consent_history_user (user_id),
    INDEX idx_consent_history_changed (changed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- cognitive_tasks
CREATE TABLE `cognitive_tasks` (
    task_id VARCHAR(20) PRIMARY KEY,
    assessment_type_id VARCHAR(20) NOT NULL,
    task_name VARCHAR(100) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    default_difficulty INT NOT NULL,
    active INT NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_task_assessment_type
        FOREIGN KEY (assessment_type_id)
        REFERENCES assessment_types(assessment_type_id),
    INDEX idx_task_assessment_type (assessment_type_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- assessment_sessions
CREATE TABLE `assessment_sessions` (
    session_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    assessment_type_id VARCHAR(20) NOT NULL,
    started_at DATETIME(6) NOT NULL,
    completed_at DATETIME(6) NULL,
    session_status VARCHAR(20) NOT NULL,
    difficulty_level INT NOT NULL,
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
    INDEX idx_session_user_date (user_id, started_at),
    INDEX idx_session_assessment (assessment_type_id),
    INDEX idx_session_status (session_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- cognitive_responses
CREATE TABLE `cognitive_responses` (
    response_id VARCHAR(20) PRIMARY KEY,
    session_id VARCHAR(20) NOT NULL,
    task_id VARCHAR(20) NOT NULL,
    trial_number INT NOT NULL,
    stimulus_type VARCHAR(50),
    response_type VARCHAR(50),
    is_correct INT NOT NULL,
    reaction_time_ms DECIMAL(10,2),
    response_value VARCHAR(255),
    omission INT NOT NULL DEFAULT FALSE,
    recorded_at DATETIME(6) NOT NULL,
    CONSTRAINT fk_response_session
        FOREIGN KEY (session_id)
        REFERENCES assessment_sessions(session_id),
    CONSTRAINT fk_response_task
        FOREIGN KEY (task_id)
        REFERENCES cognitive_tasks(task_id),
    INDEX idx_response_session (session_id),
    INDEX idx_response_task (task_id),
    UNIQUE KEY uq_response_session_trial (session_id, trial_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- cognitive_results
CREATE TABLE `cognitive_results` (
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
    difficulty_level INT,
    baseline_difference DECIMAL(10,6),
    previous_session_difference DECIMAL(10,6),
    calculated_at DATETIME(6) NOT NULL,
    CONSTRAINT fk_result_session
        FOREIGN KEY (session_id)
        REFERENCES assessment_sessions(session_id),
    CONSTRAINT fk_result_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),
    CONSTRAINT fk_result_assessment
        FOREIGN KEY (assessment_type_id)
        REFERENCES assessment_types(assessment_type_id),
    CONSTRAINT uq_result_session
        UNIQUE (session_id),
    INDEX idx_result_user_date (user_id, calculated_at),
    INDEX idx_result_domain (assessment_type_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- wellbeing_checkins
CREATE TABLE `wellbeing_checkins` (
    checkin_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    recorded_at DATETIME(6) NOT NULL,
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
    INDEX idx_wellbeing_user_date (user_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- context_records
CREATE TABLE `context_records` (
    context_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    related_session_id VARCHAR(20) NULL,
    recorded_at DATETIME(6) NOT NULL,
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- intelligence_runs
CREATE TABLE `intelligence_runs` (
    run_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    product_code VARCHAR(30) NOT NULL,
    triggered_at DATETIME(6) NOT NULL,
    trigger_type VARCHAR(50) NOT NULL,
    model_or_rule_version VARCHAR(100) NOT NULL,
    input_start_date DATETIME(6),
    input_end_date DATETIME(6),
    run_status VARCHAR(30) NOT NULL,
    CONSTRAINT fk_run_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),
    INDEX idx_run_user_product (user_id, product_code),
    INDEX idx_run_triggered (triggered_at),
    INDEX idx_run_model_version (model_or_rule_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- insights
CREATE TABLE `insights` (
    insight_id VARCHAR(20) PRIMARY KEY,
    run_id VARCHAR(20) NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    product_code VARCHAR(30) NOT NULL,
    insight_type VARCHAR(100) NOT NULL,
    insight_text TEXT NOT NULL,
    severity_or_priority VARCHAR(20),
    explanation_text TEXT,
    generated_at DATETIME(6) NOT NULL,
    CONSTRAINT fk_insight_run
        FOREIGN KEY (run_id)
        REFERENCES intelligence_runs(run_id),
    CONSTRAINT fk_insight_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),
    INDEX idx_insight_user_product (user_id, product_code),
    INDEX idx_insight_type (insight_type),
    INDEX idx_insight_generated (generated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- recommendations
CREATE TABLE `recommendations` (
    recommendation_id VARCHAR(20) PRIMARY KEY,
    insight_id VARCHAR(20) NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    product_code VARCHAR(30) NOT NULL,
    recommendation_type VARCHAR(100) NOT NULL,
    recommendation_text TEXT NOT NULL,
    priority VARCHAR(20),
    created_at DATETIME(6) NOT NULL,
    CONSTRAINT fk_recommendation_insight
        FOREIGN KEY (insight_id)
        REFERENCES insights(insight_id),
    CONSTRAINT fk_recommendation_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),
    INDEX idx_recommendation_user_product (user_id, product_code),
    INDEX idx_recommendation_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- actions
CREATE TABLE `actions` (
    action_id VARCHAR(20) PRIMARY KEY,
    recommendation_id VARCHAR(20) NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_status VARCHAR(50) NOT NULL,
    action_at DATETIME(6) NOT NULL,
    CONSTRAINT fk_action_recommendation
        FOREIGN KEY (recommendation_id)
        REFERENCES recommendations(recommendation_id),
    CONSTRAINT fk_action_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),
    INDEX idx_action_user_date (user_id, action_at),
    INDEX idx_action_recommendation (recommendation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
