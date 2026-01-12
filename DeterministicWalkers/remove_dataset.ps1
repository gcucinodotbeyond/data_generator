param (
    [Parameter(Mandatory=$true)]
    [string]$DatasetName
)

# Get the full path of the target directory
# Assuming the script is run from the project root or the dataset is relative to the script location
# If the user runs it from DeterministicWalkers, $PSScriptRoot will be correct if the script is there.
$targetDir = Join-Path -Path $PSScriptRoot -ChildPath $DatasetName

# Check if the directory exists
if (-not (Test-Path -Path $targetDir)) {
    Write-Error "Directory '$DatasetName' not found in '$PSScriptRoot'."
    exit 1
}

# Define the required subdirectories structure
$requiredSubfolders = @("hydrated-dataset", "predataset", "resources")
$missingSubfolders = @()

# Validate the structure
foreach ($subfolder in $requiredSubfolders) {
    $subfolderPath = Join-Path -Path $targetDir -ChildPath $subfolder
    if (-not (Test-Path -Path $subfolderPath)) {
        $missingSubfolders += $subfolder
    }
}

# Check if any required subfolders are missing
if ($missingSubfolders.Count -gt 0) {
    Write-Warning "The directory '$DatasetName' does not appear to be a valid dataset."
    Write-Warning "Missing subfolders: $($missingSubfolders -join ', ')"
    Write-Warning "Deletion aborted to prevent data loss."
    exit 1
}

# Confirm deletion (optional, but good practice, though user just asked to remove)
# Since it's a script for automation often, maybe force is better, but safety check is the validation above.
# I'll just remove it as requested.

try {
    Remove-Item -Path $targetDir -Recurse -Force -ErrorAction Stop
    Write-Host "Successfully removed dataset: $DatasetName" -ForegroundColor Green
}
catch {
    Write-Error "Failed to remove directory '$DatasetName'. Error: $_"
    exit 1
}
