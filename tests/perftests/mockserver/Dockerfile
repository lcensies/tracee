FROM golang:1.21.0-alpine AS builder

WORKDIR /app
COPY . .

RUN go mod download
RUN go build -o /app/mockserv

FROM alpine:latest

WORKDIR /app
COPY --from=builder /app/mockserv .

CMD ["./mockserv"]

