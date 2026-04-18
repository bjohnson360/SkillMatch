
CREATE DATABASE skillmatch;
USE skillmatch;

-- =========================================
-- TABLE: Users
-- =========================================
CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    location VARCHAR(100),
    experience_level VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user'
);

-- =========================================
-- TABLE: Project
-- =========================================
CREATE TABLE Project (
    project_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    difficulty VARCHAR(50),
    status VARCHAR(50) NOT NULL,
    owner_id INT NULL,
    CONSTRAINT fk_project_owner
        FOREIGN KEY (owner_id) REFERENCES Users(user_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

-- =========================================
-- TABLE: Skill
-- =========================================
CREATE TABLE Skill (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(100) NOT NULL
);

-- =========================================
-- TABLE: Application
-- A user can apply to a project only once
-- =========================================
CREATE TABLE Application (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    project_id INT NOT NULL,
    application_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL,
    CONSTRAINT fk_application_user
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_application_project
        FOREIGN KEY (project_id) REFERENCES Project(project_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT uq_user_project_application
        UNIQUE (user_id, project_id)
);

-- =========================================
-- TABLE: UserSkill
-- Associative entity between Users and Skill
-- =========================================
CREATE TABLE UserSkill (
    user_id INT NOT NULL,
    skill_id INT NOT NULL,
    proficiency_level INT NOT NULL,
    PRIMARY KEY (user_id, skill_id),
    CONSTRAINT fk_userskill_user
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_userskill_skill
        FOREIGN KEY (skill_id) REFERENCES Skill(skill_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT chk_userskill_proficiency
        CHECK (proficiency_level BETWEEN 1 AND 5)
);

-- =========================================
-- TABLE: ProjectSkill
-- Associative entity between Project and Skill
-- =========================================
CREATE TABLE ProjectSkill (
    project_id INT NOT NULL,
    skill_id INT NOT NULL,
    required_level INT NOT NULL,
    PRIMARY KEY (project_id, skill_id),
    CONSTRAINT fk_projectskill_project
        FOREIGN KEY (project_id) REFERENCES Project(project_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_projectskill_skill
        FOREIGN KEY (skill_id) REFERENCES Skill(skill_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT chk_projectskill_required
        CHECK (required_level BETWEEN 1 AND 5)
);

-- =========================================
-- OPTIONAL INDEXES FOR PERFORMANCE
-- =========================================
CREATE INDEX idx_users_experience_level ON Users(experience_level);
CREATE INDEX idx_users_role ON Users(role);
CREATE INDEX idx_project_status ON Project(status);
CREATE INDEX idx_skill_category ON Skill(category);
CREATE INDEX idx_application_status ON Application(status);

-- =========================================
-- STARTER DATA
-- =========================================

INSERT INTO Users (name, email, location, experience_level, role) VALUES
('Brian Johnson', 'brian@example.com', 'Atlanta', 'Graduate', 'user'),
('Alice Carter', 'alice@example.com', 'Atlanta', 'Junior', 'user'),
('David Lee', 'david@example.com', 'Remote', 'Intermediate', 'user'),
('Maya Patel', 'maya@example.com', 'New York', 'Senior', 'user');

INSERT INTO Skill (skill_name, category) VALUES
('Python', 'Programming Language'),
('SQL', 'Database'),
('Flask', 'Framework'),
('JavaScript', 'Frontend'),
('React', 'Frontend'),
('AWS', 'Cloud'),
('Java', 'Programming Language');

INSERT INTO Project (title, description, difficulty, status) VALUES
('Resume Matcher', 'Matches resumes to project and job requirements', 'Medium', 'Open'),
('Study Group Finder', 'Helps students find study partners based on interests and skills', 'Easy', 'Open'),
('Hackathon Team Builder', 'Matches users into hackathon teams based on technical fit', 'Hard', 'Open'),
('Internship Tracker', 'Tracks internship applications and opportunities', 'Medium', 'Closed');

INSERT INTO UserSkill (user_id, skill_id, proficiency_level) VALUES
(1, 1, 4),
(1, 2, 4),
(1, 3, 3),
(2, 2, 3),
(2, 4, 4),
(3, 1, 5),
(3, 6, 3),
(4, 2, 5),
(4, 5, 4);

INSERT INTO ProjectSkill (project_id, skill_id, required_level) VALUES
(1, 1, 3),
(1, 2, 3),
(1, 3, 2),
(2, 2, 2),
(2, 4, 2),
(3, 1, 4),
(3, 5, 3),
(3, 6, 2),
(4, 2, 3),
(4, 7, 2);

INSERT INTO Application (user_id, project_id, application_date, status) VALUES
(1, 1, '2026-04-01', 'Submitted'),
(2, 2, '2026-04-02', 'Interview'),
(3, 3, '2026-04-03', 'Submitted'),
(1, 4, '2026-04-04', 'Rejected'),
(4, 1, '2026-04-05', 'Accepted');

-- =========================================
-- MILESTONE 1 MIGRATION FOR EXISTING DATABASES
-- Run these only if your tables already exist
-- =========================================
/*
ALTER TABLE Users
ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user';

ALTER TABLE Project
ADD COLUMN owner_id INT NULL,
ADD CONSTRAINT fk_project_owner
    FOREIGN KEY (owner_id) REFERENCES Users(user_id)
    ON DELETE SET NULL
    ON UPDATE CASCADE;

UPDATE Users
SET role = 'user'
WHERE role IS NULL OR role = '';
*/

-- =========================================
-- TEST QUERIES
-- =========================================

SELECT * FROM Users;
SELECT * FROM Project;
SELECT * FROM Skill;
SELECT * FROM Application;
SELECT * FROM UserSkill;
SELECT * FROM ProjectSkill;

-- JOIN QUERY
SELECT U.name, P.title, A.status, A.application_date
FROM Application A
JOIN Users U ON A.user_id = U.user_id
JOIN Project P ON A.project_id = P.project_id;

-- AGGREGATE QUERY
SELECT P.title, COUNT(A.application_id) AS total_applications
FROM Project P
LEFT JOIN Application A ON P.project_id = A.project_id
GROUP BY P.project_id, P.title;
