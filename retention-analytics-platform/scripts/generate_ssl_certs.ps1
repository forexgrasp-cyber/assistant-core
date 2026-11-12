param(
    [string]$OutDir = "infra/docker/nginx/ssl",
    [string]$Domain = "localhost"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

$cert = New-SelfSignedCertificate `
    -DnsName $Domain, "*.${Domain}", "dev.localhost" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter (Get-Date).AddYears(1) `
    -KeyUsage DigitalSignature, KeyEncipherment `
    -KeyAlgorithm RSA -KeyLength 2048

$pwd = ConvertTo-SecureString -String "retention-dev" -Force -AsPlainText
Export-PfxCertificate -Cert "Cert:\CurrentUser\My\$($cert.Thumbprint)" -FilePath "$OutDir/dev.pfx" -Password $pwd | Out-Null

$certPath = "Cert:\CurrentUser\My\$($cert.Thumbprint)"
Export-Certificate -Cert $certPath -FilePath "$OutDir/dev.crt" | Out-Null

openssl pkcs12 -in "$OutDir/dev.pfx" -nocerts -out "$OutDir/dev.key" -nodes -passin pass:retention-dev 2>$null
if ($LASTEXITCODE -ne 0) {
    & openssl pkcs12 -in "$OutDir/dev.pfx" -nocerts -out "$OutDir/dev.key" -nodes -passin pass:retention-dev
}

Write-Host "SSL certs generated in $OutDir (dev.crt, dev.key)"
Write-Host "For production, replace with Let's Encrypt certs."
Remove-Item "$OutDir/dev.pfx" -ErrorAction SilentlyContinue
