import os
import logging
import pickle
import spacy
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("Downloading spaCy model...")
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Model file path
MODEL_PATH = Path("ai_model.pkl")

# Sample training data for DevOps assistant
TRAINING_DATA = [
    # GitLab related queries
    ("How do I create a GitLab pipeline?", "gitlab_pipeline"),
    ("Setup CI/CD in GitLab", "gitlab_pipeline"),
    ("Configure GitLab runners", "gitlab_runner"),
    ("How to automate tests with GitLab?", "gitlab_pipeline"),
    ("Create a merge request in GitLab", "gitlab_merge"),
    ("How do I deploy to production with GitLab?", "gitlab_deploy"),
    
    # GitHub related queries
    ("Create a GitHub repository", "github_repo"),
    ("Setup GitHub Actions", "github_actions"),
    ("Configure GitHub Pages", "github_pages"),
    ("How to use GitHub Codespaces?", "github_codespaces"),
    ("GitHub workflow automation", "github_actions"),
    ("GitHub package publishing", "github_packages"),
    
    # DevOps general questions
    ("What is continuous integration?", "devops_info"),
    ("Explain continuous deployment", "devops_info"),
    ("DevOps best practices", "devops_info"),
    ("How to automate testing?", "devops_testing"),
    ("Infrastructure as code tools", "devops_iac"),
    ("Container orchestration solutions", "devops_containers"),
    
    # Integration related queries
    ("Connect GitHub and GitLab", "integration"),
    ("Cross-platform DevOps setup", "integration"),
    ("Using GitHub and GitLab together", "integration"),
    ("OAuth between GitLab and GitHub", "integration"),
    ("API tokens for GitLab", "gitlab_auth"),
    ("GitHub authentication to GitLab", "integration"),
    
    # Help and basic queries
    ("Help me with DevOps", "help"),
    ("What can you do?", "help"),
    ("Tell me about yourself", "help"),
    ("Show my projects", "projects"),
    ("List recent actions", "actions"),
    ("Create a new project", "project_create"),
]

# Response templates
RESPONSES = {
    "gitlab_pipeline": "To create a GitLab pipeline, you need to define a `.gitlab-ci.yml` file in your repository. I can generate one for you based on your project needs. Would you like me to show you an example?",
    
    "gitlab_runner": "GitLab Runners execute your CI/CD jobs. To configure a runner, you need to register it with your GitLab instance. I can guide you through setting up runners for different environments.",
    
    "gitlab_merge": "To create a merge request in GitLab, navigate to the 'Merge Requests' section in your project, click 'New merge request', select source and target branches, add a title and description, then submit.",
    
    "gitlab_deploy": "For production deployments with GitLab, you can define deployment stages in your `.gitlab-ci.yml` file with environment configurations. Would you like me to show how to set up a deployment pipeline?",
    
    "github_repo": "I can help you create a GitHub repository through the API. Please provide a name and description for your new repository, and I'll set it up for you.",
    
    "github_actions": "GitHub Actions automate your workflow. You define workflows in YAML files in the `.github/workflows/` directory. I can create workflow files for CI/CD, testing, or deployment based on your needs.",
    
    "github_pages": "GitHub Pages lets you host websites directly from your repository. To set it up, create a branch named `gh-pages` or configure your main branch in the repository settings.",
    
    "github_codespaces": "GitHub Codespaces provides cloud-based development environments. You can configure it with a `.devcontainer/devcontainer.json` file. I can help you set up a custom environment for your project.",
    
    "github_packages": "GitHub Packages allows you to publish and consume packages. You can configure package publishing in your GitHub Actions workflow. Would you like me to show you how to publish packages?",
    
    "devops_info": "DevOps integrates development and operations to shorten the development lifecycle. It emphasizes automation, collaboration, and monitoring. Would you like more specific information about any DevOps practice?",
    
    "devops_testing": "Automated testing is crucial for DevOps. You can use tools like Pytest for Python, Jest for JavaScript, or JUnit for Java. These can be integrated into your CI/CD pipelines in both GitHub Actions and GitLab CI.",
    
    "devops_iac": "Infrastructure as Code (IaC) tools like Terraform, Ansible, or CloudFormation allow you to manage infrastructure through code rather than manual processes. This ensures consistency and reproducibility.",
    
    "devops_containers": "Container orchestration solutions like Kubernetes or Docker Swarm help manage containerized applications. They handle scaling, networking, and service discovery automatically.",
    
    "integration": "To integrate GitHub and GitLab, you can use API tokens stored in GitHub Secrets. This allows GitHub Actions to interact with GitLab repositories and pipelines. I can help you set up cross-platform workflows.",
    
    "gitlab_auth": "For GitLab authentication, you need to create a Personal Access Token with appropriate permissions. This token can be stored in GitHub Secrets and used in GitHub Actions to authenticate with GitLab API.",
    
    "help": "I'm your DevOps AI assistant that helps integrate GitHub and GitLab workflows. I can help you create repositories, set up CI/CD pipelines, manage deployments, and automate DevOps tasks across both platforms.",
    
    "projects": "I can show you a list of your projects across GitHub and GitLab. Would you like me to fetch them for you?",
    
    "actions": "I can show you recent DevOps actions that have been executed. Would you like me to display them?",
    
    "project_create": "I can help you create a new project across GitHub and GitLab with synchronized repositories. Would you like me to walk you through the process?"
}

def preprocess_text(text):
    """Process text using spaCy for better NLP features."""
    doc = nlp(text)
    # Keep only nouns, verbs, adjectives and adverbs
    tokens = [token.lemma_ for token in doc if token.pos_ in ('NOUN', 'VERB', 'ADJ', 'ADV') and not token.is_stop]
    return " ".join(tokens)

def train():
    """Train the AI model on the sample data."""
    # Extract features and labels
    texts = [item[0] for item in TRAINING_DATA]
    labels = [item[1] for item in TRAINING_DATA]
    
    # Create a pipeline with TF-IDF and Naive Bayes
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(preprocessor=preprocess_text)),
        ('clf', MultinomialNB())
    ])
    
    # Train the model
    pipeline.fit(texts, labels)
    
    # Save the model
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(pipeline, f)
    
    logger.info("Model trained and saved successfully")
    return pipeline

def load_model():
    """Load the trained model or train a new one if it doesn't exist."""
    if MODEL_PATH.exists():
        try:
            with open(MODEL_PATH, 'rb') as f:
                return pickle.load(f)
        except (pickle.UnpicklingError, EOFError):
            logger.warning("Error loading model. Training a new one.")
            return train()
    else:
        logger.info("Model not found. Training a new one.")
        return train()

def process_message(message):
    """Process a user message and return an appropriate response."""
    # Load the model
    model = load_model()
    
    # Predict the intent
    intent = model.predict([message])[0]
    
    # Get probabilities to check confidence
    proba = model.predict_proba([message])[0]
    max_proba = max(proba)
    
    # If confidence is low, return a generic response
    if max_proba < 0.3:
        return "I'm not sure I understand your request. Could you provide more details about what you need help with in your DevOps workflow?"
    
    # Return the appropriate response based on intent
    return RESPONSES.get(intent, "I'm still learning about DevOps integration. Could you try rephrasing your question?")

if __name__ == "__main__":
    # Train the model if run directly
    train()
