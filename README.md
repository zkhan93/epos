# epos

A simple Flask application that parses data from the Indian state Bihar government's "epos bihar" website and converts it into an API. This API is then used in a simple frontend built with Vue.js 2, to present the data in a mobile-friendly and user-friendly responsive site. The application is using Docker-compose to run the web, worker, flower and redis services.

## Features
- Parses data from the "epos bihar" website
- Converts data into a simple API
- Frontend built with Vue.js 2 for a mobile-friendly and user-friendly experience
- Uses caching to avoid parsing pages that are less likely to change
- Docker Compose to run the web, worker, flower and redis services

## Installation

- Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) on your system
- Clone the repository and navigate into the project directory
- Run `docker-compose up` to start the application

## Usage

The application can be accessed by going to the url `https://epos.khancave.in`

## Monitoring

- Flower dashboard is available

## Contributing

If you want to contribute to the project, please fork the repository and create a pull request with your changes.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT)
