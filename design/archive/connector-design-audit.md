### Suggestions for Improved Robustness
1. Promote "Incremental Fetching" to a Core Requirement
   - Observation: The document lists "Incremental Fetching" as a future enhancement. However, for many sources (especially high-volume ones like RSS or Twitter), fetching the same max_items_per_fetch on every run is inefficient and can lead to hitting rate limits unnecessarily.
   - Suggestion: This should be a core part of the BaseConnector contract.
Modify the run or fetch_raw_data method to accept a last_seen_id or last_fetch_timestamp.
   - The core pipeline would be responsible for storing and retrieving this "high-water mark" for each source.
   - The BaseConnector.run method could look like this:

```python
async def run(self) -> Dict[str, int]:
	last_state = await self.db.get_source_fetch_state(self.source.id) # e.g., {'last_seen_id': 'xyz'}
    # ... fetch logic using last_state
    new_items = await self.fetch_and_process(last_state)
    # ...
    await self.db.update_source_fetch_state(self.source.id, new_state)
    return stats
	
	- This dramatically improves efficiency and is a hallmark of a robust data ingestion system.

2. Clarify the content_hash Scope
   - Observation: The Post model has a content_hash for deduplication. The document implies this is a hash of the content field.
   - Suggestion: Be explicit about what constitutes a unique post. Is it just the content? Or is it a combination of source_id, title, and content? A hash of only the content could lead to incorrect-but-plausible deduplication if two different sources syndicate the same article. A more robust hash might be: sha256(f"{post.source_id}:{post.url_or_guid}:{post.content}")
3. Specify Async Library for Email Connector
   - Observation: The "Email Connector" spec lists imaplib as a dependency. imaplib is a synchronous library and will block the entire asyncio event loop, defeating the purpose of the async architecture.
   - Suggestion: Explicitly require an async IMAP library, such as aioimaplib. This is a critical detail for maintaining the performance and responsiveness of the system.
   
### Suggestions for Improved Simplicity & Maintainability
1. Implement a Template Method Pattern in BaseConnector
   - Observation: The BaseConnector defines fetch_raw_data and normalize_to_post as abstract methods, but the run method is also abstract. This forces every single connector to re-implement the same orchestration logic: fetch -> normalize -> check duplicate -> save. This is repetitive and error-prone.
   - Suggestion: Implement the run method in the BaseConnector itself. This change makes individual connectors incredibly simple: they only need to provide the fetch and normalize logic, and the base class handles the rest.
2. Clarify the Role of Source.url
   - Observation: The Source model has a url field, which makes perfect sense for RSS, Podcasts, and YouTube. However, for sources like X/Twitter (handle) or Email (server address), url is ambiguous. The example config for Twitter shows a twitter.com URL.
   - Suggestion: Rename url to a more generic term like identifier or target.
	 - Source.identifier: str
	 - This avoids confusion and makes it clear that the field's meaning is interpreted by the specific connector (e.g., for RSS it's a URL, for Twitter it's a handle, for Email it's user@imap.server.com).
