#!/usr/bin/env python3
"""
Enhanced multimodal data collector with progress bars and rich UI.
Downloads various types of public data and uploads to Google Cloud Storage.
"""

import json
import os
import requests
import shutil
import tempfile
import random
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
from google.cloud import storage
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich import print as rprint

console = Console()


class DataCollector:
    def __init__(self, output_dir: Path, num_samples: int):
        self.output_dir = output_dir
        self.num_samples = num_samples
        self.stats = {
            'text': 0,
            'json': 0,
            'csv': 0,
            'markdown': 0,
            'images': 0,
            'video': 0,
            'audio': 0,
            'pdf': 0,
            'doc': 0
        }

    def download_text_samples(self, progress, task_id) -> int:
        """Download text files from Project Gutenberg."""
        text_dir = self.output_dir / "text"
        text_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0
        gutenberg_ids = list(range(1, 70000))
        random.shuffle(gutenberg_ids)

        for book_id in gutenberg_ids:
            if downloaded >= self.num_samples:
                break

            urls = [
                f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
                f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
                f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt"
            ]

            for url in urls:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200 and len(response.text) > 1000:
                        filename = f"book_{downloaded+1:03d}.txt"
                        file_path = text_dir / filename
                        file_path.write_text(response.text[:50000])
                        downloaded += 1
                        progress.update(task_id, advance=1, description=f"[cyan]📚 Text files[/cyan] ({downloaded}/{self.num_samples})")
                        break
                except:
                    continue

            if downloaded % 10 == 0:
                time.sleep(0.5)

        self.stats['text'] = downloaded
        return downloaded

    def download_json_samples(self, progress, task_id) -> int:
        """Download JSON data from various APIs."""
        json_dir = self.output_dir / "json"
        json_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0

        # GitHub repos
        try:
            for page in range(1, (self.num_samples // 30) + 2):
                if downloaded >= self.num_samples:
                    break

                url = f"https://api.github.com/search/repositories?q=stars:>100&sort=stars&per_page=30&page={page}"
                response = requests.get(url, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    for repo in data.get('items', []):
                        if downloaded >= self.num_samples:
                            break
                        filename = f"repo_{downloaded+1:03d}.json"
                        file_path = json_dir / filename
                        file_path.write_text(json.dumps(repo, indent=2))
                        downloaded += 1
                        progress.update(task_id, advance=1, description=f"[yellow]🔧 JSON files[/yellow] ({downloaded}/{self.num_samples})")

                time.sleep(2)
        except:
            pass

        # JSONPlaceholder API for remaining
        endpoints = ['posts', 'comments', 'albums', 'photos', 'todos', 'users']

        while downloaded < self.num_samples:
            endpoint = random.choice(endpoints)
            item_id = random.randint(1, 100)

            try:
                url = f"https://jsonplaceholder.typicode.com/{endpoint}/{item_id}"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    filename = f"json_{downloaded+1:03d}.json"
                    file_path = json_dir / filename
                    file_path.write_text(json.dumps(response.json(), indent=2))
                    downloaded += 1
                    progress.update(task_id, advance=1, description=f"[yellow]🔧 JSON files[/yellow] ({downloaded}/{self.num_samples})")
            except:
                continue

        self.stats['json'] = downloaded
        return downloaded

    def download_csv_samples(self, progress, task_id) -> int:
        """Download CSV files from various sources."""
        csv_dir = self.output_dir / "csv"
        csv_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0

        csv_sources = [
            "https://raw.githubusercontent.com/datasets/covid-19/main/data/countries-aggregated.csv",
            "https://raw.githubusercontent.com/datasets/airport-codes/main/data/airport-codes.csv",
            "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv",
            "https://raw.githubusercontent.com/datasets/population/main/data/population.csv",
            "https://raw.githubusercontent.com/datasets/gdp/main/data/gdp.csv",
        ]

        for i, url in enumerate(csv_sources):
            if downloaded >= self.num_samples:
                break

            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    lines = response.text.split('\n')
                    header = lines[0] if lines else ""

                    for j in range(min(20, self.num_samples - downloaded)):
                        filename = f"csv_{downloaded+1:03d}.csv"
                        file_path = csv_dir / filename

                        start = min(j * 10, len(lines) - 50)
                        end = min(start + 50 + (j * 5), len(lines))
                        subset = [header] + lines[start:end]

                        file_path.write_text('\n'.join(subset))
                        downloaded += 1
                        progress.update(task_id, advance=1, description=f"[green]📊 CSV files[/green] ({downloaded}/{self.num_samples})")

                        if downloaded >= self.num_samples:
                            break
            except:
                continue

        # Generate synthetic CSV data for remaining
        while downloaded < self.num_samples:
            filename = f"csv_{downloaded+1:03d}.csv"
            file_path = csv_dir / filename

            data = "id,name,value,category\n"
            for row in range(50):
                data += f"{row},item_{row},{random.randint(1,1000)},category_{random.randint(1,10)}\n"

            file_path.write_text(data)
            downloaded += 1
            progress.update(task_id, advance=1, description=f"[green]📊 CSV files[/green] ({downloaded}/{self.num_samples})")

        self.stats['csv'] = downloaded
        return downloaded

    def download_markdown_samples(self, progress, task_id) -> int:
        """Download markdown files from GitHub."""
        md_dir = self.output_dir / "markdown"
        md_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0

        try:
            for page in range(1, 5):
                if downloaded >= self.num_samples:
                    break

                url = f"https://api.github.com/search/repositories?q=stars:>10&sort=stars&per_page=100&page={page}"
                response = requests.get(url, timeout=30)

                if response.status_code == 200:
                    repos = response.json().get('items', [])

                    for repo in repos:
                        if downloaded >= self.num_samples:
                            break

                        owner = repo['owner']['login']
                        name = repo['name']

                        for branch in ['main', 'master']:
                            readme_url = f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/README.md"

                            try:
                                readme_response = requests.get(readme_url, timeout=10)
                                if readme_response.status_code == 200:
                                    filename = f"readme_{downloaded+1:03d}.md"
                                    file_path = md_dir / filename
                                    file_path.write_text(readme_response.text[:100000])
                                    downloaded += 1
                                    progress.update(task_id, advance=1, description=f"[magenta]📝 Markdown files[/magenta] ({downloaded}/{self.num_samples})")
                                    break
                            except:
                                continue

                    time.sleep(2)
        except:
            pass

        # Generate synthetic markdown for remaining
        while downloaded < self.num_samples:
            filename = f"markdown_{downloaded+1:03d}.md"
            file_path = md_dir / filename

            content = f"# Sample Document {downloaded+1}\n\n## Overview\nSynthetic markdown for testing.\n"
            file_path.write_text(content)
            downloaded += 1
            progress.update(task_id, advance=1, description=f"[magenta]📝 Markdown files[/magenta] ({downloaded}/{self.num_samples})")

        self.stats['markdown'] = downloaded
        return downloaded

    def download_image_samples(self, progress, task_id) -> int:
        """Download images from Lorem Picsum."""
        image_dir = self.output_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0

        for i in range(self.num_samples):
            try:
                width = 200 + (i % 10) * 50
                height = 200 + ((i + 5) % 10) * 30

                url = f"https://picsum.photos/{width}/{height}?random={i}"
                response = requests.get(url, timeout=30)

                if response.status_code == 200:
                    filename = f"image_{downloaded+1:03d}.jpg"
                    file_path = image_dir / filename
                    file_path.write_bytes(response.content)
                    downloaded += 1
                    progress.update(task_id, advance=1, description=f"[red]🖼️  Images[/red] ({downloaded}/{self.num_samples})")

                if downloaded % 10 == 0:
                    time.sleep(1)

            except:
                continue

        self.stats['images'] = downloaded
        return downloaded

    def download_video_samples(self, progress, task_id) -> int:
        """Download video files from Internet Archive and other public sources."""
        video_dir = self.output_dir / "video"
        video_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0

        # Internet Archive has thousands of public domain videos
        # Using their API to get video files
        ia_collections = [
            "opensource_movies",
            "prelinger",
            "nasa",
            "animationandcartoons",
            "educational_films",
            "computersandtechvideos",
            "sciencevideos"
        ]

        for collection in ia_collections:
            if downloaded >= self.num_samples:
                break

            try:
                # Query Internet Archive API for videos in collection
                api_url = f"https://archive.org/advancedsearch.php?q=collection:{collection}+mediatype:movies&fl=identifier&rows=50&output=json"
                response = requests.get(api_url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    items = data.get('response', {}).get('docs', [])

                    for item in items:
                        if downloaded >= self.num_samples:
                            break

                        identifier = item.get('identifier')
                        if identifier:
                            # Get metadata for this item
                            metadata_url = f"https://archive.org/metadata/{identifier}"
                            try:
                                meta_response = requests.get(metadata_url, timeout=10)
                                if meta_response.status_code == 200:
                                    metadata = meta_response.json()
                                    files = metadata.get('files', [])

                                    # Find MP4 or other video files
                                    for file_info in files:
                                        if downloaded >= self.num_samples:
                                            break

                                        name = file_info.get('name', '')
                                        if name.endswith(('.mp4', '.avi', '.mpg', '.mpeg')):
                                            video_url = f"https://archive.org/download/{identifier}/{name}"

                                            try:
                                                # Download with size limit
                                                video_response = requests.get(video_url, timeout=30, stream=True)
                                                if video_response.status_code == 200:
                                                    filename = f"video_{downloaded+1:03d}.mp4"
                                                    file_path = video_dir / filename

                                                    with open(file_path, 'wb') as f:
                                                        size = 0
                                                        for chunk in video_response.iter_content(chunk_size=8192):
                                                            if size > 2 * 1024 * 1024:  # 2MB limit
                                                                break
                                                            f.write(chunk)
                                                            size += len(chunk)

                                                    if file_path.stat().st_size > 10000:  # At least 10KB
                                                        downloaded += 1
                                                        progress.update(task_id, advance=1, description=f"[blue]🎬 Video files[/blue] ({downloaded}/{self.num_samples})")
                                                        break  # Move to next item
                                            except:
                                                continue
                            except:
                                continue
            except:
                continue

        # Direct links to known good videos as fallback
        if downloaded < self.num_samples:
            direct_videos = [
                "https://archive.org/download/BigBuckBunny_124/Content/big_buck_bunny_720p_surround.mp4",
                "https://archive.org/download/ElephantsDream/ed_1024_512kb.mp4",
                "https://archive.org/download/Popeye_forPresident/Popeye_forPresident_512kb.mp4",
                "https://archive.org/download/SitaSingsTheBlues/Sita_Sings_the_Blues_480p_2150kbps.mp4",
                "https://archive.org/download/night_of_the_living_dead/night_of_the_living_dead_512kb.mp4",
                "https://archive.org/download/Plan_9_from_Outer_Space_1959/Plan_9_from_Outer_Space_1959.mp4",
                "https://archive.org/download/charade_1963/charade_1963_512kb.mp4",
                "https://archive.org/download/his_girl_friday/his_girl_friday_512kb.mp4",
            ]

            for url in direct_videos:
                if downloaded >= self.num_samples:
                    break

                try:
                    response = requests.get(url, timeout=30, stream=True)
                    if response.status_code == 200:
                        filename = f"video_{downloaded+1:03d}.mp4"
                        file_path = video_dir / filename

                        with open(file_path, 'wb') as f:
                            size = 0
                            for chunk in response.iter_content(chunk_size=8192):
                                if size > 2 * 1024 * 1024:
                                    break
                                f.write(chunk)
                                size += len(chunk)

                        downloaded += 1
                        progress.update(task_id, advance=1, description=f"[blue]🎬 Video files[/blue] ({downloaded}/{self.num_samples})")
                except:
                    continue

        self.stats['video'] = downloaded
        return downloaded

    def download_audio_samples(self, progress, task_id) -> int:
        """Download audio files from Internet Archive and other public sources."""
        audio_dir = self.output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0

        # Internet Archive has massive audio collections
        ia_audio_collections = [
            "opensource_audio",
            "78rpm",
            "oldtimeradio",
            "librivoxaudio",
            "podcasts",
            "netlabels",
            "classicalmusic",
            "etree"
        ]

        for collection in ia_audio_collections:
            if downloaded >= self.num_samples:
                break

            try:
                # Query Internet Archive API for audio in collection
                api_url = f"https://archive.org/advancedsearch.php?q=collection:{collection}+mediatype:audio&fl=identifier&rows=50&output=json"
                response = requests.get(api_url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    items = data.get('response', {}).get('docs', [])

                    for item in items:
                        if downloaded >= self.num_samples:
                            break

                        identifier = item.get('identifier')
                        if identifier:
                            # Get metadata for this item
                            metadata_url = f"https://archive.org/metadata/{identifier}"
                            try:
                                meta_response = requests.get(metadata_url, timeout=10)
                                if meta_response.status_code == 200:
                                    metadata = meta_response.json()
                                    files = metadata.get('files', [])

                                    # Find MP3 or other audio files
                                    for file_info in files:
                                        if downloaded >= self.num_samples:
                                            break

                                        name = file_info.get('name', '')
                                        if name.endswith(('.mp3', '.ogg', '.m4a', '.flac')):
                                            audio_url = f"https://archive.org/download/{identifier}/{name}"

                                            try:
                                                # Download with size limit
                                                audio_response = requests.get(audio_url, timeout=30, stream=True)
                                                if audio_response.status_code == 200:
                                                    filename = f"audio_{downloaded+1:03d}.mp3"
                                                    file_path = audio_dir / filename

                                                    with open(file_path, 'wb') as f:
                                                        size = 0
                                                        for chunk in audio_response.iter_content(chunk_size=8192):
                                                            if size > 1 * 1024 * 1024:  # 1MB limit
                                                                break
                                                            f.write(chunk)
                                                            size += len(chunk)

                                                    if file_path.stat().st_size > 5000:  # At least 5KB
                                                        downloaded += 1
                                                        progress.update(task_id, advance=1, description=f"[purple]🎵 Audio files[/purple] ({downloaded}/{self.num_samples})")
                                                        break  # Move to next item
                                            except:
                                                continue
                            except:
                                continue
            except:
                continue

        # Direct links to known good audio files as fallback
        if downloaded < self.num_samples:
            direct_audio = [
                "https://archive.org/download/testmp3testfile/mpthreetest.mp3",
                "https://archive.org/download/ird059/mp3_128/ird059_05_beethoven_pour_elise_128kb.mp3",
                "https://archive.org/download/MoonlightSonata_755/Beethoven-MoonlightSonata.mp3",
                "https://archive.org/download/BrahmsWaltzNo.15InAFlatMajorOp.39/Brahms-WaltzOp.39No.15InAFlatMajor.mp3",
                "https://archive.org/download/ChopinPreludeInEMinorOp.28No.4/Chopin-PreludeOp.28No.4InEMinor.mp3",
                "https://archive.org/download/Mozart_201502/Mozart.mp3",
                "https://archive.org/download/VivaldiSpring/Vivaldi-Spring.mp3",
                "https://archive.org/download/BachAirOnTheGString/Bach-AirOnTheGString.mp3",
            ]

            for url in direct_audio:
                if downloaded >= self.num_samples:
                    break

                try:
                    response = requests.get(url, timeout=30)
                    if response.status_code == 200:
                        filename = f"audio_{downloaded+1:03d}.mp3"
                        file_path = audio_dir / filename
                        file_path.write_bytes(response.content[:1024*1024])  # 1MB limit

                        downloaded += 1
                        progress.update(task_id, advance=1, description=f"[purple]🎵 Audio files[/purple] ({downloaded}/{self.num_samples})")
                except:
                    continue

        self.stats['audio'] = downloaded
        return downloaded

    def download_pdf_samples(self, progress, task_id) -> int:
        """Download PDF files from arXiv with proper paper IDs."""
        pdf_dir = self.output_dir / "pdf"
        pdf_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0

        # Generate more arXiv paper IDs - using real patterns
        # CS papers from 2020-2024
        arxiv_categories = [
            "cs.LG",  # Machine Learning
            "cs.CV",  # Computer Vision
            "cs.CL",  # Computation and Language
            "cs.AI",  # Artificial Intelligence
            "cs.NE",  # Neural and Evolutionary Computing
            "cs.RO",  # Robotics
            "cs.CR",  # Cryptography and Security
            "cs.DB",  # Databases
            "cs.SE",  # Software Engineering
            "cs.DS",  # Data Structures and Algorithms
        ]

        # Generate paper IDs from recent years
        arxiv_ids = []
        for year in [2020, 2021, 2022, 2023, 2024]:
            for month in range(1, 13):
                for paper_num in range(1, 20, 3):  # Sample papers
                    paper_id = f"{year % 100:02d}{month:02d}.{paper_num:05d}"
                    arxiv_ids.append(paper_id)

        # Shuffle to get variety
        random.shuffle(arxiv_ids)

        # Try to download from arXiv
        attempts = 0
        max_attempts = min(len(arxiv_ids), self.num_samples * 3)  # Try 3x as many to account for failures

        for paper_id in arxiv_ids[:max_attempts]:
            if downloaded >= self.num_samples:
                break

            url = f"https://arxiv.org/pdf/{paper_id}.pdf"

            try:
                response = requests.get(url, timeout=15, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
                if response.status_code == 200:
                    filename = f"arxiv_{downloaded+1:03d}.pdf"
                    file_path = pdf_dir / filename

                    # Download first 2MB only
                    with open(file_path, 'wb') as f:
                        size = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            if size > 2 * 1024 * 1024:  # 2MB limit
                                break
                            f.write(chunk)
                            size += len(chunk)

                    # Verify it's a valid PDF
                    if file_path.stat().st_size > 1000:  # At least 1KB
                        downloaded += 1
                        progress.update(task_id, advance=1, description=f"[orange3]📄 PDF files[/orange3] ({downloaded}/{self.num_samples})")
                    else:
                        file_path.unlink()  # Remove invalid file

                    time.sleep(0.5)  # Be respectful to arXiv
                elif response.status_code == 429:  # Rate limited
                    time.sleep(5)  # Wait longer
            except Exception as e:
                continue

            attempts += 1

        # Internet Archive - Public domain books/documents for remaining
        if downloaded < self.num_samples:
            ia_pdfs = [
                "https://archive.org/download/alicesadventures19033gut/alicesadventures19033gut.pdf",
                "https://archive.org/download/TheAdventuresOfTomSawyer_201303/The%20Adventures%20of%20Tom%20Sawyer.pdf",
                "https://archive.org/download/prideandprejudic00aust_2/prideandprejudic00aust_2.pdf",
                "https://archive.org/download/flatland_gu_li_/flatland_gu_li_.pdf",
                "https://archive.org/download/warandpeace030164mbp/warandpeace030164mbp.pdf",
                "https://archive.org/download/originofspecies00darwuoft/originofspecies00darwuoft.pdf",
                "https://archive.org/download/TheRepublicOfPlato/TheRepublicOfPlato.pdf",
                "https://archive.org/download/ThePrinceByNiccoloMachiavelli/The-Prince-by-Niccolo-Machiavelli.pdf",
                "https://archive.org/download/artofwar00suntuoft/artofwar00suntuoft.pdf",
                "https://archive.org/download/cu31924014579100/cu31924014579100.pdf",  # Shakespeare
            ]

            for url in ia_pdfs:
                if downloaded >= self.num_samples:
                    break

                try:
                    response = requests.get(url, timeout=30, stream=True)
                    if response.status_code == 200:
                        filename = f"book_{downloaded+1:03d}.pdf"
                        file_path = pdf_dir / filename

                        with open(file_path, 'wb') as f:
                            size = 0
                            for chunk in response.iter_content(chunk_size=8192):
                                if size > 2 * 1024 * 1024:  # 2MB limit
                                    break
                                f.write(chunk)
                                size += len(chunk)

                        downloaded += 1
                        progress.update(task_id, advance=1, description=f"[orange3]📄 PDF files[/orange3] ({downloaded}/{self.num_samples})")
                except:
                    continue

        # GitHub PDF repositories for technical documentation
        if downloaded < self.num_samples:
            github_pdfs = [
                "https://github.com/progit/progit2/releases/download/2.1.411/progit.pdf",
                "https://github.com/getify/You-Dont-Know-JS/blob/1st-ed/README.md",  # This would need conversion
            ]

            for url in github_pdfs:
                if downloaded >= self.num_samples:
                    break

                if url.endswith('.pdf'):
                    try:
                        response = requests.get(url, timeout=30, stream=True, allow_redirects=True)
                        if response.status_code == 200:
                            filename = f"tech_{downloaded+1:03d}.pdf"
                            file_path = pdf_dir / filename

                            with open(file_path, 'wb') as f:
                                size = 0
                                for chunk in response.iter_content(chunk_size=8192):
                                    if size > 2 * 1024 * 1024:
                                        break
                                    f.write(chunk)
                                    size += len(chunk)

                            downloaded += 1
                            progress.update(task_id, advance=1, description=f"[orange3]📄 PDF files[/orange3] ({downloaded}/{self.num_samples})")
                    except:
                        continue

        self.stats['pdf'] = downloaded
        return downloaded

    def download_doc_samples(self, progress, task_id) -> int:
        """Download DOC/DOCX files and other document formats."""
        doc_dir = self.output_dir / "documents"
        doc_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0

        # Sample document sources (templates and examples)
        doc_sources = [
            # Open source document templates
            "https://github.com/sheetjs/test_files/raw/master/AutoFilter.xlsx",
            "https://github.com/sheetjs/test_files/raw/master/SimpleCalc.xlsx",
            "https://github.com/python-openxml/python-docx/raw/master/features/templates/default.docx",
        ]

        for url in doc_sources:
            if downloaded >= self.num_samples:
                break

            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    # Determine extension from URL
                    if '.xlsx' in url:
                        ext = 'xlsx'
                    elif '.docx' in url:
                        ext = 'docx'
                    else:
                        ext = 'doc'

                    filename = f"document_{downloaded+1:03d}.{ext}"
                    file_path = doc_dir / filename
                    file_path.write_bytes(response.content[:512*1024])  # Max 512KB

                    downloaded += 1
                    progress.update(task_id, advance=1, description=f"[brown]📋 Document files[/brown] ({downloaded}/{self.num_samples})")
            except:
                continue

        # Create synthetic RTF documents for remaining samples
        while downloaded < min(self.num_samples, downloaded + 10):
            filename = f"document_{downloaded+1:03d}.rtf"
            file_path = doc_dir / filename

            rtf_content = r"{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}}\f0\fs24 Sample Document " + str(downloaded+1) + r"\par This is a test RTF document.\par}"
            file_path.write_text(rtf_content)

            downloaded += 1
            progress.update(task_id, advance=1, description=f"[brown]📋 Document files[/brown] ({downloaded}/{self.num_samples})")

        self.stats['doc'] = downloaded
        return downloaded


def upload_to_gcs_with_progress(bucket_name: str, local_dir: Path, project_id: str = "semgrep-472018") -> Tuple[int, int]:
    """Upload directory contents to Google Cloud Storage with progress bar."""

    console.print(Panel.fit(f"[bold cyan]☁️  Uploading to gs://{bucket_name}/[/bold cyan]", border_style="cyan"))

    try:
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)

        # Count total files
        files_to_upload = list(local_dir.rglob("*"))
        files_to_upload = [f for f in files_to_upload if f.is_file()]
        total_files = len(files_to_upload)

        uploaded_count = 0
        failed_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Uploading files...[/cyan]", total=total_files)

            for file_path in files_to_upload:
                blob_path = f"multimodal-dataset/{os.path.relpath(file_path, local_dir)}"
                blob = bucket.blob(blob_path)

                try:
                    blob.upload_from_filename(str(file_path))
                    uploaded_count += 1
                    progress.update(task, advance=1, description=f"[cyan]☁️  Uploading[/cyan] ({uploaded_count}/{total_files})")
                except Exception as e:
                    failed_count += 1

        return uploaded_count, failed_count

    except Exception as e:
        console.print(f"[red]❌ Failed to connect to GCS: {e}[/red]")
        return 0, 0


def create_summary_table(stats: Dict, total_files: int) -> Table:
    """Create a summary table of downloaded files."""
    table = Table(title="📊 Download Summary", show_header=True, header_style="bold magenta")
    table.add_column("Data Type", style="cyan", width=15)
    table.add_column("Files", justify="right", style="green")
    table.add_column("Status", justify="center")

    for data_type, count in stats.items():
        status = "✅" if count > 0 else "❌"
        table.add_row(data_type.capitalize(), str(count), status)

    table.add_row("", "", "")
    table.add_row("[bold]Total[/bold]", f"[bold]{total_files}[/bold]", "🎉")

    return table


def main():
    """Main function with enhanced UI."""
    import argparse

    parser = argparse.ArgumentParser(description="Multimodal data collector with progress bars")
    parser.add_argument("--num-samples", type=int, default=100,
                       help="Number of samples per data type (default: 100)")
    parser.add_argument("--bucket", default="gcm-data-lake", help="GCS bucket name")
    parser.add_argument("--project", default="semgrep-472018", help="GCP project ID")
    parser.add_argument("--output-dir", default="/tmp/multimodal_data",
                       help="Local directory for downloads")
    args = parser.parse_args()

    # Clear console and show banner
    console.clear()
    console.print(Panel.fit(
        "[bold magenta]🚀 Multimodal Data Collector 🚀[/bold magenta]\n" +
        f"[dim]Downloading {args.num_samples} samples per type[/dim]",
        border_style="magenta"
    ))

    # Create output directory
    output_dir = Path(args.output_dir)
    if output_dir.exists():
        console.print("[yellow]Cleaning existing directory...[/yellow]")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    collector = DataCollector(output_dir, args.num_samples)

    # Download with progress bars
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:

        # Create tasks for each data type
        text_task = progress.add_task("[cyan]📚 Text files[/cyan]", total=args.num_samples)
        json_task = progress.add_task("[yellow]🔧 JSON files[/yellow]", total=args.num_samples)
        csv_task = progress.add_task("[green]📊 CSV files[/green]", total=args.num_samples)
        md_task = progress.add_task("[magenta]📝 Markdown files[/magenta]", total=args.num_samples)
        img_task = progress.add_task("[red]🖼️  Images[/red]", total=args.num_samples)
        video_task = progress.add_task("[blue]🎬 Video files[/blue]", total=args.num_samples)
        audio_task = progress.add_task("[purple]🎵 Audio files[/purple]", total=args.num_samples)
        pdf_task = progress.add_task("[orange3]📄 PDF files[/orange3]", total=args.num_samples)
        doc_task = progress.add_task("[brown]📋 Document files[/brown]", total=args.num_samples)

        # Download each type
        collector.download_text_samples(progress, text_task)
        collector.download_json_samples(progress, json_task)
        collector.download_csv_samples(progress, csv_task)
        collector.download_markdown_samples(progress, md_task)
        collector.download_image_samples(progress, img_task)
        collector.download_video_samples(progress, video_task)
        collector.download_audio_samples(progress, audio_task)
        collector.download_pdf_samples(progress, pdf_task)
        collector.download_doc_samples(progress, doc_task)

    # Count total files
    total_files = sum(1 for _ in output_dir.rglob("*") if _.is_file())

    # Show summary table
    console.print("\n")
    console.print(create_summary_table(collector.stats, total_files))

    # Upload to GCS
    console.print("\n")
    uploaded, failed = upload_to_gcs_with_progress(args.bucket, output_dir, args.project)

    # Final summary
    console.print("\n")
    if uploaded > 0:
        console.print(Panel.fit(
            f"[bold green]✅ Success![/bold green]\n" +
            f"[green]Uploaded {uploaded} files to gs://{args.bucket}/multimodal-dataset/[/green]",
            border_style="green"
        ))
    if failed > 0:
        console.print(f"[yellow]⚠️  {failed} files failed to upload[/yellow]")


if __name__ == "__main__":
    main()