#!/bin/bash
# This assumes the docker containers have already been brough up
source .env
docker compose down
docker compose up -d minio

echo "Waiting for MinIO to start..."
pingcount=0
until docker exec -it crab-minio curl -s -f -o /dev/null "http://localhost:9000/minio/health/live"
do
        symbol="|"
        case $(($pingcount % 4)) in
        0)
                symbol="/"
                ;;
        1)
                symbol="-"
                ;;
        2)
                symbol="\\"
                ;;
        3)
                symbol="|"
                ;;
        esac
        secs=$(($pingcount/10))
        echo -en "\rStill waiting for MinIO to start $symbol [$secs s]"
        pingcount=$(($pingcount+1))
        sleep 0.1
done
echo ""
echo "MinIO started!"
MC_ALIAS="local"
source .env
docker exec -it crab-minio mc alias set $MC_ALIAS "$S3_ENDPOINT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
docker exec -it crab-minio mc admin user add $MC_ALIAS "$S3_ACCESS_KEY" "$S3_SECRET_KEY"
docker exec -it crab-minio mc mb $MC_ALIAS/$S3_BUCKET
cat > crab-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "*"
        ]
      },
      "Action": [
        "s3:GetBucketLocation",
        "s3:ListBucket",
        "s3:ListBucketMultipartUploads"
      ],
      "Resource": [
        "arn:aws:s3:::$S3_BUCKET"
      ]
    },
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "*"
        ]
      },
      "Action": [
        "s3:AbortMultipartUpload",
        "s3:DeleteObject",
        "s3:GetObject",
        "s3:ListMultipartUploadParts",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::$S3_BUCKET/*"
      ]
    }
  ]
}
EOF
docker cp crab-policy.json crab-minio:/tmp/crab-policy.json
docker exec -it crab-minio mc admin policy create $MC_ALIAS crab-policy /tmp/crab-policy.json
docker exec -it crab-minio mc admin policy attach $MC_ALIAS crab-policy --user "$S3_ACCESS_KEY"
rm crab-policy.json
docker exec -it crab-minio mc anonymous set download $MC_ALIAS/$S3_BUCKET
