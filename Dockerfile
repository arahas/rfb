FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port for Streamlit (default is 8501)
EXPOSE 8501

# Set the default command to run the Streamlit dashboard
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"] 