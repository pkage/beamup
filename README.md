# beamup

super simple uploader to s3 compatible services

## setup

```
$ pipx install git+https://github.com/pkage/beamup
```

then, in `~/.config/beamup/beam_config.toml`, place the following:

```toml
[profile.default]
region     = "nyc3"
endpoint   = "https://nyc3.digitaloceanspaces.com"
access_key = "your_access_key"
secret_key = "your_secret_key"
bucket     = "your_bucket"
prefix     = "uploads"
access_url = "https://cdn.example.com/"
```
