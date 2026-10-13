
pipeline {
    agent any

    options {
        timestamps()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Check Python') {
            steps {
                bat 'python --version'
            }
        }

        stage('Install Dependencies') {
            steps {
                bat 'python -m pip install -r requirements-dev.txt'
            }
        }

        stage('Validate Python') {
            steps {
                bat 'python -m compileall -q src tests'
            }
        }

        stage('Run Tests') {
            steps {
                bat 'python -m pytest -v'
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
