
FROM python:3.10

# Set working directory
WORKDIR /app

# Copy everything into the container
COPY . .

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose Streamlit default port
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "chart_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
