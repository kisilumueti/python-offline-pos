from app import create_app

app = create_app()

if __name__ == '__main__':
    # Write logs to a file to see what's wrong
    try:
        app.run(debug=False, host='127.0.0.1', port=5000)
    except Exception as e:
        with open("error_log.txt", "w") as f:
            f.write(str(e))
