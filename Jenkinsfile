pipeline {
agent any

options {
    timestamps()
}

environment {
    PYTHON = 'C:\\Users\\NALANDA\\AppData\\Local\\Programs\\Python\\Python312\\python.exe'
}

stages {
    stage('Checkout') {
        steps {
            checkout scm
        }
    }

    stage('Check Python') {
        steps {
            bat '"%PYTHON%" --version'
        }
    }

    stage('Create Virtual Environment') {
        steps {
            bat '"%PYTHON%" -m venv .venv'
        }
    }

    stage('Install Dependencies') {
        steps {
            bat '".venv\\Scripts\\python.exe" -m pip install -r requirements-dev.txt'
        }
    }

    stage('Validate Python') {
        steps {
            bat '".venv\\Scripts\\python.exe" -m compileall -q src tests'
        }
    }

    stage('Run Tests') {
        steps {
            bat '".venv\\Scripts\\python.exe" -m pytest -v'
        }
    }
}

post {
    success {
        echo 'SUCCESS: All project tests passed.'
    }
    failure {
        echo 'FAILURE: Check the Console Output.'
    }
}

}