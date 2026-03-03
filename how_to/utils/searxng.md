# What and Why SearxNG?

SearxNG is a privacy-focused search metasearch engine that allows you to search the web without revealing your personal information. It is a self-hosted alternative to Google and other search engines, and it is free to use.

It is a metasearch engine, which means it searches multiple search engines at once and returns the results in a single list. Bypassing the limits of a single search engine, it can provide a more comprehensive and diverse search experience.

We use **SearxNG** to give the agent a browser-like experience, allowing it to search the world wide web for vast information retrieval. This is an optional tool, and it is not required for the agent to function.

# How to set up SearxNG

### Useful Resources

* **What is Docker?** [https://docs.docker.com/get-started/docker-overview/](https://docs.docker.com/get-started/docker-overview/)
* **Get Docker:** [https://docs.docker.com/get-started/get-docker/](https://docs.docker.com/get-started/get-docker/)

* **SearxNG Official Documentation:** [https://docs.searxng.org/index.html](https://docs.searxng.org/index.html)
* **Install SearxNG Docker, GitHub:** [https://github.com/searxng/searxng-docker](https://github.com/searxng/searxng-docker)


### Tips

The **searxng-docker GitHub page** Includes a lot of useful information and instructions for setting up SearxNG, including settings for advanced users.

Follow the general installation instructions on the **searxng-docker GitHub page** linked above (cloning the repository, etc.). Here are the instructions adapted from the searxng-docker GitHub page:

1.  Get docker

    [Install docker](https://docs.docker.com/get-started/get-docker/)


2. Get searxng-docker

```shell
cd /usr/local
git clone https://github.com/searxng/searxng-docker.git
cd searxng-docker
```

3.  Update the `settings.yml` file to enable programmatic access.
    In your local copy of `settings.yml`, add the following lines:

```yaml
search:
  safe_search: 1
  formats:
    - html
    - json # This is the most important line, it allows for programmatic retrieval.
```

4. Create a secret key and update it in the `settings.yml` file.
  The command to generate the secret key (and replace the placeholder in `settings.yml`) is shown below:

**For Linux:**

```bash
sed -i "s|ultrasecretkey|$(openssl rand -hex 32)|g" searxng/settings.yml
```

**For macOS:**

```bash
sed -i '' "s|ultrasecretkey|$(openssl rand -hex 32)|g" searxng/settings.yml
```

**For Windows:**

> [!NOTE]
> Windows users can use the following powershell script to generate the secret key:
> ```powershell
> $randomBytes = New-Object byte[] 32
> (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes)
> $secretKey = -join ($randomBytes | ForEach-Object { "{0:x2}" -f $_ })
> (Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml
> ```




5. Once the key and settings.yml are updated, start the service as detailed in the Docker instructions:

```bash
docker compose up -d
```


6. The service should now be running and accessible at: http://localhost:8080
