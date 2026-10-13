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
                bat '"C:\\Users\\NALANDA\\AppData\\Local\\Microsoft\\WindowsApps\\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\\python.exe" --version'
            }
        }

        stage('Install Dependencies') {
            steps {
                bat '"C:\\Users\\NALANDA\\AppData\\Local\\Microsoft\\WindowsApps\\PythonSoftwareFoundation\\Python.3.13_qbz5n2kfra8p0\\python.exe" -m pip install -r requirements-dev.txt'
            }
        }

        stage('Validate Python') {
            steps {
                bat '"C:\\Users\\NALANDA\\AppData\\Local\\Microsoft\\WindowsApps\\PythonSoftwareFoundation\\Python.3.13_qbz5n2kfra8p0\\python.exe" -m compileall -q src tests'
            }
        }

        stage('Run Tests') {
            steps {
                bat '"C:\\Users\\NALANDA\\AppData\\Local\\Microsoft\\WindowsApps\\PythonSoftwareFoundation\\Python.3.13_qbz5n2kfra8p0\\python.exe" -m pytest -v'
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