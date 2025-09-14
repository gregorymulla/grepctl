"""
download_upload_resources.py
================================

This script automates the creation of a small, public‑data–based “data lake”
suitable for demonstrating multimodal semantic search tools such as Semgrep.

The dataset includes:

* **Chat conversations** – 100 chat transcripts extracted from the Cornell
  Movie‑Dialogs Corpus.  This corpus contains more than 220 000 lines of
  dialogue from movie scripts【648181046024994†L25-L34】, making it a convenient
  source of fictitious conversations.
* **Audio clips** – 100 spoken‑language recordings sampled from Mozilla’s
  Common Voice project.  Common Voice publishes multilingual voice clips
  “under a CC0 license”【932704623435764†L25-L31】, meaning the data are free to
  use without cost or copyright restriction.
* **Video clips** – 100 short videos from the UCF101 dataset.  UCF101
  comprises 13 320 videos across 101 human‑action categories and is
  distributed under a Creative Commons Attribution–NonCommercial 4.0 licence
  (CC BY‑NC 4.0)【145063388458164†L168-L199】.
* **PDF documents** – 100 scholarly papers fetched from the arXiv API.  The
  arXiv API exists to “allow programmatic access to the arXiv’s e‑print
  content and metadata”【528574580792516†L215-L231】, providing a simple way to
  download open‑access research papers.
* **Markdown files** – 100 README files from popular public GitHub
  repositories.  GitHub’s REST API exposes an endpoint to “get a repository
  README”【127973877505140†L845-L871】 for any public repository, which this
  script leverages to fetch markdown content.

After downloading and preparing these resources, the script uploads them to
your Google Cloud Storage (GCS) bucket.  You must have a GCS bucket created
and configured with appropriate permissions, and your environment must be
authenticated to GCP (for example by setting the `GOOGLE_APPLICATION_CREDENTIALS`
environment variable to point at a service‑account JSON key).

Usage
-----

The script can be executed directly from the command line.  For example:

```
python download_upload_resources.py \
    --bucket my‑demo‑bucket \
    --output_dir /tmp/semgrep_data \
    --num_samples 100
```

If you omit `--output_dir`, a temporary directory is created.  The `--num_samples`
parameter controls how many items of each modality are downloaded (default 100).

Dependencies
------------

* `google‑cloud‑storage` – for uploading to GCS.
* `arxiv` – for searching and downloading papers from arXiv.
* `datasets` – for downloading Common Voice audio samples.
* `tensorflow‑datasets` and `imageio` – for downloading and writing UCF101 video clips.

Install them via pip:

```
pip install google‑cloud‑storage arxiv datasets tensorflow‑datasets imageio
```

Note: downloading UCF101 and Common Voice will consume several gigabytes
of disk space and bandwidth.  If you only need to test the script, reduce
`--num_samples` to a small number (e.g. 5).
"""

import argparse
import base64
import io
import json
import os
import random
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List

import requests

# Third‑party libraries: these imports will fail if the packages are not installed.
try:
    from google.cloud import storage
except ImportError:
    storage = None  # type: ignore

try:
    import arxiv
except ImportError:
    arxiv = None  # type: ignore

try:
    import datasets
except ImportError:
    datasets = None  # type: ignore

try:
    import tensorflow_datasets as tfds
except ImportError:
    tfds = None  # type: ignore

try:
    import imageio
except ImportError:
    imageio = None  # type: ignore


def download_cornell_conversations(target_dir: Path, num_samples: int = 100) -> None:
    """Download the Cornell Movie‑Dialogs Corpus and extract a subset of conversations.

    The dataset comprises several text files.  Two of them are used here:

    * `movie_lines.txt` – contains individual lines of dialogue with metadata.
    * `movie_conversations.txt` – contains lists of utterance IDs that together
      form a conversation.

    This function downloads the corpus zip, extracts it into `target_dir`,
    samples the specified number of conversations, and writes each conversation
    into its own text file under `target_dir/chats`.
    """
    # Source archive URL for the Cornell Movie‑Dialogs Corpus
    url = "http://www.cs.cornell.edu/~cristian/data/cornell_movie_dialogs_corpus.zip"
    zip_path = target_dir / "cornell_movie_dialogs_corpus.zip"
    extract_dir = target_dir / "cornell_movie_dialogs_corpus"

    # Download the zip file if it doesn't already exist
    if not zip_path.exists():
        print(f"Downloading Cornell Movie‑Dialogs Corpus from {url}…")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
    else:
        print("Cornell dataset archive already downloaded.")

    # Extract the archive
    if not extract_dir.exists():
        print("Extracting Cornell Movie‑Dialogs Corpus…")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(target_dir)
    else:
        print("Cornell dataset already extracted.")

    # Load dialogue lines into a mapping from line ID to text
    # The files are extracted directly to target_dir, not in a subdirectory
    lines_file = target_dir / "cornell movie-dialogs corpus" / "movie_lines.txt"
    conversations_file = target_dir / "cornell movie-dialogs corpus" / "movie_conversations.txt"

    lines_map: Dict[str, str] = {}
    with open(lines_file, "r", encoding="iso-8859-1") as f:
        for line in f:
            parts = line.strip().split(" +++$+++ ")
            if len(parts) >= 5:
                line_id = parts[0]
                text = parts[4]
                lines_map[line_id] = text

    # Build a list of conversations (list of utterance strings)
    conversations: List[List[str]] = []
    with open(conversations_file, "r", encoding="iso-8859-1") as f:
        for line in f:
            parts = line.strip().split(" +++$+++ ")
            if len(parts) >= 4:
                utter_ids_raw = parts[3]
                # Remove square brackets and quotes then split on comma
                utter_ids = (
                    utter_ids_raw.strip()[1:-1]  # remove surrounding []
                    .replace("'", "")
                    .split(", ")
                )
                conversation = [lines_map.get(uid, "") for uid in utter_ids]
                conversations.append(conversation)

    # Shuffle and select the desired number of conversations
    random.shuffle(conversations)
    conversations = conversations[: num_samples]

    # Write each conversation to its own file
    chats_dir = target_dir / "chats"
    chats_dir.mkdir(parents=True, exist_ok=True)
    for idx, conv in enumerate(conversations, 1):
        file_path = chats_dir / f"chat_{idx:03d}.txt"
        with open(file_path, "w", encoding="utf-8") as out_f:
            out_f.write("\n".join(conv))
    print(f"Saved {len(conversations)} chat transcripts to {chats_dir}.")


def download_common_voice_audio(target_dir: Path, num_samples: int = 100, language: str = "en") -> None:
    """Download audio clips from the Mozilla Common Voice dataset.

    Uses the `datasets` library to fetch a subset of the Common Voice
    corpus.  Each record contains an `audio` field with a file path.  The
    function copies these audio files into `target_dir/audio`.

    :param target_dir: Directory in which the audio files will be stored.
    :param num_samples: Number of audio samples to download.
    :param language: Language code for Common Voice (e.g., "en" for English).
    """
    if datasets is None:
        raise ImportError(
            "The 'datasets' package is required for downloading Common Voice audio.\n"
            "Install it via `pip install datasets` and try again."
        )
    print(f"Loading {num_samples} Common Voice samples (language={language})…")
    ds = datasets.load_dataset(
        "mozilla-foundation/common_voice_11_0", language, split=f"train[:{num_samples}]"
    )
    audio_dir = target_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    for idx, record in enumerate(ds, 1):
        audio_info = record["audio"]
        src_path = audio_info["path"]
        # Copy the audio file into our output directory
        dst_path = audio_dir / f"audio_{idx:03d}.wav"
        shutil.copy(src_path, dst_path)
    print(f"Saved {num_samples} audio files to {audio_dir}.")


def download_ucf_videos(target_dir: Path, num_samples: int = 100) -> None:
    """Download video clips from the UCF101 dataset.

    The UCF101 dataset contains over 13 000 videos across 101 human actions【145063388458164†L168-L199】.
    This function uses TensorFlow Datasets (`tensorflow_datasets`) to fetch the
    dataset and save the first `num_samples` videos as MP4 files in
    `target_dir/video`.

    :param target_dir: Directory in which the video files will be stored.
    :param num_samples: Number of videos to download.
    """
    if tfds is None or imageio is None:
        raise ImportError(
            "The 'tensorflow-datasets' and 'imageio' packages are required for downloading UCF101.\n"
            "Install them via `pip install tensorflow-datasets imageio` and try again."
        )
    print(f"Loading UCF101 dataset and extracting {num_samples} videos…")
    ds = tfds.load("ucf101", split="train", as_supervised=False)
    video_dir = target_dir / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    for idx, example in enumerate(ds.take(num_samples), 1):
        video_tensor = example["video"].numpy()  # shape: (num_frames, H, W, 3)
        fps = 24  # default frames per second
        output_path = video_dir / f"video_{idx:03d}.mp4"
        # Write video using imageio
        imageio.mimsave(output_path, video_tensor, fps=fps)
    print(f"Saved {num_samples} video files to {video_dir}.")


def download_arxiv_papers(target_dir: Path, num_samples: int = 100, category: str = "cs.CL") -> None:
    """Download a set of PDF papers from arXiv using the arxiv package.

    :param target_dir: Directory in which the PDFs will be stored.
    :param num_samples: Number of papers to download.
    :param category: arXiv category (e.g., 'cs.CL' for Computation and Language).
    """
    if arxiv is None:
        raise ImportError(
            "The 'arxiv' package is required for downloading papers.\n"
            "Install it via `pip install arxiv` and try again."
        )
    print(f"Querying arXiv for the latest {num_samples} papers in category {category}…")
    search = arxiv.Search(
        query=f"cat:{category}",
        max_results=num_samples,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    pdf_dir = target_dir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    for idx, result in enumerate(search.results(), 1):
        filename = pdf_dir / f"paper_{idx:03d}.pdf"
        try:
            result.download_pdf(dirpath=str(pdf_dir), filename=filename.name)
        except Exception as e:
            print(f"Failed to download {result.entry_id}: {e}")
    print(f"Saved {num_samples} PDF files to {pdf_dir}.")


def download_github_readmes(target_dir: Path, num_samples: int = 100) -> None:
    """Download README.md files from popular public GitHub repositories.

    GitHub’s REST API exposes an endpoint to fetch the preferred README of any
    repository【127973877505140†L845-L871】.  This function queries the GitHub
    Search API for repositories with many stars and downloads their README
    contents (base64‑encoded) into individual `.md` files.

    :param target_dir: Directory in which the markdown files will be stored.
    :param num_samples: Number of repositories to process.
    """
    print(f"Searching GitHub for the top {num_samples} starred repositories…")
    repos: List[Dict] = []
    page = 1
    per_page = 100  # GitHub API maximum per page
    while len(repos) < num_samples:
        search_url = (
            f"https://api.github.com/search/repositories"
            f"?q=stars:>1&sort=stars&order=desc&per_page={per_page}&page={page}"
        )
        resp = requests.get(search_url)
        if resp.status_code != 200:
            raise RuntimeError(f"GitHub API request failed: {resp.status_code} {resp.text}")
        data = resp.json()
        repos.extend(data.get("items", []))
        page += 1
    repos = repos[: num_samples]

    md_dir = target_dir / "markdown"
    md_dir.mkdir(parents=True, exist_ok=True)
    for idx, repo in enumerate(repos, 1):
        owner = repo["owner"]["login"]
        name = repo["name"]
        readme_url = f"https://api.github.com/repos/{owner}/{name}/readme"
        readme_resp = requests.get(readme_url)
        if readme_resp.status_code != 200:
            print(f"Skipping {owner}/{name}: unable to fetch README (status {readme_resp.status_code}).")
            continue
        content = readme_resp.json().get("content")
        encoding = readme_resp.json().get("encoding")
        if content and encoding == "base64":
            md_bytes = base64.b64decode(content)
            md_path = md_dir / f"readme_{idx:03d}.md"
            with open(md_path, "wb") as f:
                f.write(md_bytes)
        else:
            print(f"Skipping {owner}/{name}: README missing or not base64 encoded.")
    print(f"Saved {len(list(md_dir.glob('*.md')))} markdown files to {md_dir}.")


def upload_directory_to_gcs(bucket_name: str, local_dir: Path) -> None:
    """Upload a directory tree to a Google Cloud Storage bucket.

    Recursively walks the directory `local_dir`, uploading each file to a blob
    whose path matches the file’s relative path within `local_dir`.  Requires
    the `google-cloud-storage` package and a valid GCP environment (set
    `GOOGLE_APPLICATION_CREDENTIALS` or otherwise authenticate).
    """
    if storage is None:
        raise ImportError(
            "The 'google‑cloud‑storage' package is required for uploading to GCS.\n"
            "Install it via `pip install google‑cloud‑storage` and try again."
        )
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    print(f"Uploading contents of {local_dir} to gs://{bucket_name}…")
    for root, _, files in os.walk(local_dir):
        for file_name in files:
            file_path = Path(root) / file_name
            blob_path = os.path.relpath(file_path, local_dir)
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(str(file_path))
    print(f"Upload complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and upload multimodal demo data to GCS.")
    parser.add_argument("--bucket", required=True, help="Name of the destination GCS bucket.")
    parser.add_argument(
        "--output_dir",
        default=None,
        help="Local directory to store downloaded data (defaults to a temporary directory).",
    )
    parser.add_argument(
        "--num_samples",
        type=int,
        default=100,
        help="Number of items per modality to download (default: 100).",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language code for Common Voice audio (default: 'en').",
    )
    parser.add_argument(
        "--arxiv_category",
        default="cs.CL",
        help="arXiv category to download papers from (default: 'cs.CL').",
    )
    args = parser.parse_args()

    # Determine the output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path(tempfile.mkdtemp(prefix="semgrep_data_"))
    print(f"Data will be stored in {output_dir}")

    # Download each modality
    download_cornell_conversations(output_dir, num_samples=args.num_samples)
    download_common_voice_audio(output_dir, num_samples=args.num_samples, language=args.language)
    download_ucf_videos(output_dir, num_samples=args.num_samples)
    download_arxiv_papers(output_dir, num_samples=args.num_samples, category=args.arxiv_category)
    download_github_readmes(output_dir, num_samples=args.num_samples)

    # Upload to GCS
    upload_directory_to_gcs(args.bucket, output_dir)


if __name__ == "__main__":
    main()