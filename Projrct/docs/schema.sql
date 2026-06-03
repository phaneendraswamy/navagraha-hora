CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(160) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(60),
    linkedin_url VARCHAR(255),
    github_url VARCHAR(255),
    portfolio_url VARCHAR(255),
    location VARCHAR(160),
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE skills (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(80) NOT NULL,
    name VARCHAR(120) NOT NULL,
    proficiency VARCHAR(80)
);

CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(180) NOT NULL,
    domain VARCHAR(120),
    description TEXT NOT NULL,
    technologies TEXT DEFAULT '',
    business_impact TEXT,
    keywords TEXT DEFAULT '',
    role_tags TEXT DEFAULT ''
);

CREATE TABLE experiences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company VARCHAR(180) NOT NULL,
    role VARCHAR(180) NOT NULL,
    duration VARCHAR(120) NOT NULL,
    responsibilities TEXT NOT NULL,
    achievements TEXT DEFAULT '',
    technologies TEXT DEFAULT ''
);

CREATE TABLE certifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(180) NOT NULL,
    organization VARCHAR(180),
    skills_covered TEXT DEFAULT ''
);

CREATE TABLE education (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    degree VARCHAR(180) NOT NULL,
    institution VARCHAR(180) NOT NULL,
    duration VARCHAR(120),
    gpa VARCHAR(40)
);

CREATE TABLE jd_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    raw_text TEXT NOT NULL,
    parsed_json TEXT DEFAULT '{}',
    role_type VARCHAR(80),
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE resumes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jd_history_id INTEGER REFERENCES jd_history(id) ON DELETE SET NULL,
    target_role VARCHAR(80) NOT NULL,
    template_name VARCHAR(80) NOT NULL,
    ats_score FLOAT DEFAULT 0,
    docx_path VARCHAR(255),
    pdf_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT now()
);
