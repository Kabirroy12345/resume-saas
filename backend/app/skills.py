# backend/app/skills.py

# Master skill list (100+ skills across roles)
SKILLS = [
    # Core languages
    "python", "java", "c", "c++", "c#", "javascript", "typescript",
    "go", "rust", "kotlin", "swift", "ruby", "php", "r",

    # Frontend
    "html", "css", "sass", "less", "tailwind", "bootstrap",
    "react", "nextjs", "vue", "angular", "svelte", "jquery",

    # Backend / APIs
    "node", "express", "django", "flask", "spring", "fastapi",
    "laravel", ".net", "asp.net", "graphql", "rest api",

    # Databases
    "mysql", "postgresql", "sqlite", "mongodb", "redis", "oracle",
    "sql server", "firebase",

    # Cloud / DevOps
    "aws", "azure", "gcp",
    "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "github actions", "gitlab ci",
    "ci/cd", "devops",

    # OS / scripting
    "linux", "bash", "powershell",

    # Data / ML / AI
    "machine learning", "deep learning", "nlp", "computer vision",
    "data analysis", "pandas", "numpy", "scikit-learn",
    "tensorflow", "pytorch",

    # BI / analytics
    "tableau", "power bi", "excel",

    # Messaging / streaming
    "kafka", "rabbitmq",

    # Mobile
    "android", "ios", "flutter", "react native", "swiftui",

    # Blockchain / Web3
    "blockchain", "solidity", "hyperledger", "web3",

    # Security
    "cybersecurity", "penetration testing", "network security",

    # Generic SWE / tools
    "git", "github", "gitlab", "jira", "confluence",
]

# Synonyms / alternate spellings mapped to canonical skills above
SYNONYMS = {
    "js": "javascript",
    "ts": "typescript",
    "nodejs": "node",
    "node.js": "node",
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "next.js": "nextjs",
    "asp.net core": "asp.net",
    "rest": "rest api",
    "restful api": "rest api",

    "ml": "machine learning",
    "dl": "deep learning",
    "cv": "computer vision",

    "sqlserver": "sql server",
    "ms sql": "sql server",

    "amazon web services": "aws",
    "amazon aws": "aws",
    "microsoft azure": "azure",
    "google cloud": "gcp",
    "gcloud": "gcp",

    "k8s": "kubernetes",

    "ci cd": "ci/cd",
    "ci-cd": "ci/cd",
    "ci_cd": "ci/cd",
    "gitlab-ci": "gitlab ci",
    "jenkins ci": "jenkins",

    "rn": "react native",
    "expo": "react native",

    "offensive security": "cybersecurity",
    "pentesting": "penetration testing",
    "pen testing": "penetration testing",

    "hyper ledger": "hyperledger",
    "web 3": "web3",
}

# Role → indicative keywords (used to guess role/category from JD)
ROLE_KEYWORDS = {
    "Frontend Developer": [
        "frontend", "front-end", "ui developer", "react", "angular", "vue",
        "html", "css", "javascript", "typescript", "spa"
    ],
    "Backend Developer": [
        "backend", "back-end", "api developer", "microservices", "spring",
        "django", "flask", "node", "express", "database"
    ],
    "Full-Stack Developer": [
        "fullstack", "full-stack", "full stack", "frontend and backend",
        "mern", "mean", "lamp"
    ],
    "Data Scientist / ML Engineer": [
        "data scientist", "ml engineer", "machine learning", "deep learning",
        "nlp", "computer vision", "analytics", "data analysis"
    ],
    "DevOps / Cloud Engineer": [
        "devops", "cloud engineer", "site reliability", "sre",
        "kubernetes", "docker", "terraform", "ci/cd", "infrastructure"
    ],
    "Cybersecurity Engineer": [
        "security engineer", "cybersecurity", "penetration testing",
        "pen tester", "infosec", "appsec", "network security"
    ],
    "Blockchain Developer": [
        "blockchain", "solidity", "web3", "smart contract", "defi"
    ],
    "Mobile Developer": [
        "android", "ios", "mobile app", "flutter", "react native", "swiftui"
    ],
    "Software Engineer": [
        "software engineer", "software developer", "sde", "swe",
        "backend", "frontend", "fullstack"
    ],
}

