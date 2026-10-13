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
                bat '"C:\\Users\\NALANDA\\Downloads\\automatic-file-organizer-stage1m1\\automatic-file-organizer\\.venv\\Scripts\\python.exe" --version'
            }
        }

        stage('Install Dependencies') {
            steps {
                bat '"C:\\Users\\NALANDA\\Downloads\\automatic-file-organizer-stage1m1\\automatic-file-organizer\\.venv\\Scripts\\python.exe" -m pip install -r requirements-dev.txt'
            }
        }

        stage('Validate Python') {
            steps {
                bat '"C:\\Users\\NALANDA\\Downloads\\automatic-file-organizer-stage1m1\\automatic-file-organizer\\.venv\\Scripts\\python.exe" -m compileall -q src tests'
            }
        }

        stage('Run Tests') {
            steps {
                bat '"C:\\Users\\NALANDA\\Downloads\\automatic-file-organizer-stage1m1\\automatic-file-organizer\\.venv\\Scripts\\python.exe" -m pytest -v'
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
