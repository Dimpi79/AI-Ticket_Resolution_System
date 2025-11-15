from app import app

if __name__ == '__main__':
    # Run on 127.0.0.1:5001 as requested
    app.run(host="127.0.0.1", port=5001, debug=True)
