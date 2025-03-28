import os
import logging
import random
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Model file path (not used in this simplified version)
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

def find_most_similar_query(user_text):
    """Find the most similar query in our training data using simple word matching."""
    user_words = set(user_text.lower().split())
    
    best_match = None
    highest_score = 0
    
    for query, intent in TRAINING_DATA:
        query_words = set(query.lower().split())
        # Calculate a simple similarity score based on word overlap
        common_words = user_words.intersection(query_words)
        score = len(common_words) / (len(user_words) + len(query_words) - len(common_words))
        
        if score > highest_score:
            highest_score = score
            best_match = intent
    
    # Return a default intent if no good match is found
    if highest_score < 0.2:
        return "help"
    
    return best_match

def process_message(message):
    """Process a user message and return an appropriate response."""
    logger.info(f"Processing message: {message}")
    
    try:
        # Find the most similar query and get its intent
        intent = find_most_similar_query(message)
        
        # Get the response for this intent
        response = RESPONSES.get(intent, "I'm still learning about DevOps integration. Could you try rephrasing your question?")
        
        # Log what we're returning
        logger.info(f"Responding with intent: {intent}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return "I'm having trouble understanding your request right now. Could you try again with different wording?"

if __name__ == "__main__":
    # Test the model if run directly
    test_message = "How can I create a GitHub repository?"
    print(f"Test message: {test_message}")
    print(f"Response: {process_message(test_message)}")
