from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
import urllib.parse
import logging

logger = logging.getLogger(__name__)

# Initialize the FastMCP server instance for YouTube
mcp = FastMCP("YouTubeScraper")

@mcp.tool()
def fetch_youtube_transcript(video_url: str) -> str:
    """
    Fetches the full text transcript of a YouTube video given its URL. 
    Use this to summarize videos, answer specific questions about video content, 
    or extract key quotes.
    """
    try:
        # 1. Safely extract the video ID from various YouTube URL formats
        parsed_url = urllib.parse.urlparse(video_url)
        video_id = None
        
        if parsed_url.hostname in ['youtu.be', 'www.youtu.be']:
            video_id = parsed_url.path[1:]
        elif parsed_url.hostname in ['youtube.com', 'www.youtube.com']:
            video_id = urllib.parse.parse_qs(parsed_url.query).get('v', [None])[0]
            
        if not video_id:
            return "Error: Could not extract a valid YouTube video ID from the provided URL."

        # 2. Fetch the transcript from YouTube's API
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # 3. Combine the text blocks
        full_text = " ".join([t['text'] for t in transcript_list])
        
        # 4. Context Window Protection (Cap at ~15,000 characters)
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "\n\n... [TRUNCATED FOR CONTEXT SIZE]"
            
        return f"Transcript for Video {video_id}:\n{full_text}"
        
    except Exception as e:
        return f"Error fetching transcript: {str(e)}. The video might not have closed captions enabled."

if __name__ == "__main__":
    mcp.run(transport="stdio")