#!/usr/bin/env python3
"""
GitHub PR Comment Parser Utility

A utility script to fetch and parse GitHub PR comments with reaction filtering.
Uses GitHub CLI for fast and reliable API access while providing structured Python output.

Usage:
    python .github/parse_pr_comments.py --pr 11 --reaction +1 --user michaelMinar
    python .github/parse_pr_comments.py --pr 11 --bot github-actions[bot] --reaction +1

Requirements:
    - GitHub CLI (gh) installed and authenticated
    - pip install python-dotenv (optional)
"""

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CommentData:
    """Represents a GitHub comment with all relevant metadata."""
    comment_id: int
    comment_body: str
    reviewer: str
    timestamp: str
    preceding_commit: Optional[str]  # SHA of commit that preceded this comment
    preceding_commit_message: Optional[str]  # Message of the preceding commit
    file_path: Optional[str]  # For review comments
    line_number: Optional[int]  # For review comments
    comment_type: str  # 'issue' or 'review'
    html_url: str
    reactions: Dict[str, List[str]]  # reaction_type -> list of users who reacted


class GitHubCommentParser:
    """Handles fetching and parsing GitHub PR comments via GitHub CLI."""
    
    def __init__(self, repo_name: str):
        self.repo_name = repo_name
        
    def _run_gh_command(self, cmd: List[str]) -> Any:
        """Execute a GitHub CLI command and return JSON result."""
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            if result.stdout.strip():
                return json.loads(result.stdout)
            return []
        except subprocess.CalledProcessError as e:
            print(f"Error running command {' '.join(cmd)}: {e.stderr}", file=sys.stderr)
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}", file=sys.stderr)
            return []
    
    def get_pr_commits(self, pr_number: int) -> List[Dict]:
        """Get all commits for a PR."""
        return self._run_gh_command([
            "gh", "api", f"repos/{self.repo_name}/pulls/{pr_number}/commits", "--paginate"
        ])
    
    def get_preceding_commit(
        self, commits: List[Dict], comment_timestamp: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Find the commit that directly preceded a comment based on timestamp."""
        try:
            comment_dt = datetime.fromisoformat(comment_timestamp.replace('Z', '+00:00'))
            
            # Find the most recent commit before the comment timestamp
            preceding_commit = None
            for commit in commits:
                commit_dt = datetime.fromisoformat(
                    commit['commit']['author']['date'].replace('Z', '+00:00')
                )
                if commit_dt <= comment_dt:
                    if (
                        not preceding_commit or 
                        commit_dt > datetime.fromisoformat(
                            preceding_commit['commit']['author']['date'].replace('Z', '+00:00')
                        )
                    ):
                        preceding_commit = commit
            
            if preceding_commit:
                return preceding_commit['sha'], preceding_commit['commit']['message'].split('\n')[0]
            return None, None
            
        except Exception as e:
            print(f"Warning: Could not determine preceding commit: {e}")
            return None, None
    
    def get_comment_reactions(self, comment_id: int, comment_type: str) -> Dict[str, List[str]]:
        """Fetch all reactions for a specific comment."""
        if comment_type == "issue":
            endpoint = f"repos/{self.repo_name}/issues/comments/{comment_id}/reactions"
        else:  # review
            endpoint = f"repos/{self.repo_name}/pulls/comments/{comment_id}/reactions"
        
        reactions = self._run_gh_command(["gh", "api", endpoint])
        
        # Group reactions by content type
        reaction_map = {}
        for reaction in reactions:
            content = reaction["content"]
            user = reaction["user"]["login"]
            if content not in reaction_map:
                reaction_map[content] = []
            reaction_map[content].append(user)
        
        return reaction_map
    
    def get_pr_comments(self, pr_number: int) -> List[CommentData]:
        """Fetch all comments (issue + review) for a PR with full metadata."""
        comments = []
        
        print(f"Fetching PR #{pr_number} information...")
        
        # Get PR info
        pr_info = self._run_gh_command([
            "gh", "api", f"repos/{self.repo_name}/pulls/{pr_number}"
        ])
        print(f"PR Title: {pr_info.get('title', 'Unknown')}")
        
        # Get all commits for the PR
        print("Fetching PR commits...")
        commits = self.get_pr_commits(pr_number)
        print(f"Found {len(commits)} commits")
        
        # Get issue comments
        print("Fetching issue comments...")
        issue_comments = self._run_gh_command([
            "gh", "api", f"repos/{self.repo_name}/issues/{pr_number}/comments", "--paginate"
        ])
        
        for comment in issue_comments:
            # Get preceding commit
            preceding_sha, preceding_msg = self.get_preceding_commit(commits, comment["created_at"])
            
            # Get reactions
            reactions = self.get_comment_reactions(comment["id"], "issue")
            
            comments.append(CommentData(
                comment_id=comment["id"],
                comment_body=comment["body"],
                reviewer=comment["user"]["login"],
                timestamp=comment["created_at"],
                preceding_commit=preceding_sha,
                preceding_commit_message=preceding_msg,
                file_path=None,
                line_number=None,
                comment_type="issue",
                html_url=comment["html_url"],
                reactions=reactions
            ))
        
        print(f"Found {len(issue_comments)} issue comments")
        
        # Get review comments
        print("Fetching review comments...")
        review_comments = self._run_gh_command([
            "gh", "api", f"repos/{self.repo_name}/pulls/{pr_number}/comments", "--paginate"
        ])
        
        # Create a commit lookup for review comments
        commit_cache = {}
        for commit in commits:
            commit_cache[commit['sha']] = commit['commit']['message'].split('\n')[0]
        
        for comment in review_comments:
            # Get commit info for review comments
            commit_sha = comment.get("commit_id")
            commit_msg = commit_cache.get(commit_sha)
            
            # Get reactions
            reactions = self.get_comment_reactions(comment["id"], "review")
            
            comments.append(CommentData(
                comment_id=comment["id"],
                comment_body=comment["body"],
                reviewer=comment["user"]["login"],
                timestamp=comment["created_at"],
                preceding_commit=commit_sha,
                preceding_commit_message=commit_msg,
                file_path=comment.get("path"),
                line_number=comment.get("line"),
                comment_type="review",
                html_url=comment["html_url"],
                reactions=reactions
            ))
        
        print(f"Found {len(review_comments)} review comments")
        print(f"Total: {len(comments)} comments")
        return comments


def save_comments_to_file(comments: List[CommentData], output_file: Path) -> None:
    """Save comments to a JSON file, sorted by timestamp in reverse order (newest first)."""
    output_file.parent.mkdir(exist_ok=True)
    
    # Sort comments by timestamp in reverse order (newest first)
    sorted_comments = sorted(comments, key=lambda c: c.timestamp, reverse=True)
    
    # Convert dataclasses to dicts for JSON serialization
    comments_data = [asdict(comment) for comment in sorted_comments]
    
    with open(output_file, 'w') as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_comments": len(comments),
            "sorted_by": "timestamp desc (newest first)",
            "comments": comments_data
        }, f, indent=2)
    
    print(f"Saved {len(comments)} comments to {output_file} (sorted newest first)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Parse GitHub PR comments with reaction filtering")
    parser.add_argument("--pr", type=int, required=True, help="PR number")
    parser.add_argument(
        "--repo", 
        default="michaelMinar/daily-intelligence-report", 
        help="Repository (owner/name)"
    )
    parser.add_argument("--reaction", help="Filter by specific reaction type (e.g., +1, -1, heart)")
    parser.add_argument("--user", help="Filter reactions by specific user")
    parser.add_argument("--bot", help="Filter comments by specific bot user")
    parser.add_argument(
        "--output", 
        help="Output file path (default: .github/pr_comments_data.json)"
    )
    parser.add_argument(
        "--all", 
        action="store_true", 
        help="Include all comments regardless of reactions"
    )
    
    args = parser.parse_args()
    
    # Set default output file
    if not args.output:
        script_dir = Path(__file__).parent
        args.output = script_dir / "pr_comments_data.json"
    else:
        args.output = Path(args.output)
    
    parser_tool = GitHubCommentParser(args.repo)
    all_comments = parser_tool.get_pr_comments(args.pr)
    
    # Filter by bot user if specified
    if args.bot:
        all_comments = [c for c in all_comments if c.reviewer == args.bot]
        print(f"Filtered to {len(all_comments)} comments from bot: {args.bot}")
    
    # Filter by reactions if specified
    filtered_comments = []
    if args.all:
        filtered_comments = all_comments
        print(f"Including all {len(filtered_comments)} comments")
    elif args.reaction:
        for comment in all_comments:
            if args.reaction in comment.reactions:
                upvoters = comment.reactions[args.reaction]
                if args.user and args.user not in upvoters:
                    continue
                filtered_comments.append(comment)
        
        print(f"Found {len(filtered_comments)} comments with '{args.reaction}' reactions")
        if args.user:
            print(f"From user: {args.user}")
    else:
        # Default: show comments with any reactions
        for comment in all_comments:
            if comment.reactions:
                filtered_comments.append(comment)
        print(f"Found {len(filtered_comments)} comments with any reactions")
    
    # Save to file (will be sorted by timestamp)
    save_comments_to_file(filtered_comments, args.output)
    
    # Print summary (also sorted by timestamp, newest first)
    if filtered_comments:
        sorted_for_display = sorted(filtered_comments, key=lambda c: c.timestamp, reverse=True)
        print("\nSummary of comments (newest first):")
        for comment in sorted_for_display[:10]:  # Show only first 10 for brevity
            reactions_str = (
                ", ".join([f"{k}: {len(v)}" for k, v in comment.reactions.items()]) 
                if comment.reactions else "none"
            )
            file_info = f" ({comment.file_path}:{comment.line_number})" if comment.file_path else ""
            commit_info = (
                f" [commit: {comment.preceding_commit[:8]}]" 
                if comment.preceding_commit else ""
            )
            print(f"  - {comment.timestamp[:19]} | {comment.reviewer}{file_info}{commit_info}")
            print(f"    Reactions: {reactions_str}")
            print(f"    {comment.comment_body[:100]}...")
            print()
        
        if len(filtered_comments) > 10:
            print(f"    ... and {len(filtered_comments) - 10} more comments (see JSON file)")


if __name__ == "__main__":
    main()