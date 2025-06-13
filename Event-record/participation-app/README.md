# Participation App

This project is a Flask application that manages participation records using SQLAlchemy for database interactions. It provides a RESTful API for creating, retrieving, updating, and deleting participation records.

## Project Structure

```
participation-app
├── app.py                # Main application file
├── requirements.txt      # Project dependencies
└── README.md             # Project documentation
```

## Setup Instructions

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd participation-app
   ```

2. **Create a virtual environment** (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Initialize the database**:
   Run the application once to create the database and tables:
   ```
   python app.py
   ```

## Usage

- Start the Flask application:
  ```
  python app.py
  ```

- The API will be available at `http://127.0.0.1:5000/`.

### API Endpoints

- **GET /participations**: Retrieve a list of all participation records.
- **GET /participations/<int:id>**: Retrieve a specific participation record by ID.
- **POST /participations**: Create a new participation record.
- **PUT /participations/<int:id>**: Update an existing participation record by ID.
- **DELETE /participations/<int:id>**: Delete a participation record by ID.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.