FROM jaseci/jaclang:0.34.7

WORKDIR /app

COPY jac.toml ./
RUN jac install

COPY . ./

EXPOSE 10000

CMD ["sh", "-c", "jac x uvicorn bridge:app --host 0.0.0.0 --port ${PORT:-10000}"]
