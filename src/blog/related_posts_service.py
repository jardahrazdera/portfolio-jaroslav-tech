import re
from collections import defaultdict
from django.db.models import Q, Count
from django.core.cache import cache
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone
import hashlib
import logging

logger = logging.getLogger(__name__)


class RelatedPostsService:
    """
    Advanced related posts service using multiple algorithms:
    1. Content similarity analysis (TF-IDF like scoring)
    2. Tag-based relationships with weighting
    3. Category-based relationships
    4. Temporal proximity (recent posts preference)
    5. Author relationships
    """

    # Weight configuration for different similarity factors
    WEIGHTS = {
        'content_similarity': 0.35,  # Text content similarity
        'tag_similarity': 0.30,     # Shared tags
        'category_similarity': 0.20, # Shared categories
        'author_similarity': 0.10,   # Same author
        'temporal_proximity': 0.05,  # Publication time proximity
    }

    # Cache configuration
    CACHE_TIMEOUT = 3600  # 1 hour
    CACHE_PREFIX = 'related_posts'

    def __init__(self, post):
        """Initialize with the current post."""
        self.post = post
        self.cache_key = self._generate_cache_key()

    def get_related_posts(self, count=6, layout_type='default'):
        """
        Get related posts using advanced algorithm with caching.

        Args:
            count (int): Number of related posts to return
            layout_type (str): Layout type for different display contexts

        Returns:
            dict: Related posts with metadata and layout information
        """
        # Try to get from cache first
        cached_result = cache.get(self.cache_key)
        if cached_result and len(cached_result.get('posts', [])) >= count:
            return {
                **cached_result,
                'posts': cached_result['posts'][:count],
                'layout_type': layout_type,
                'cache_hit': True
            }

        # Generate related posts using multiple algorithms
        related_posts = self._calculate_related_posts(count * 2)  # Get more for better selection

        # Enhance posts with additional metadata
        enhanced_posts = self._enhance_posts_metadata(related_posts[:count])

        # Prepare result with layout-specific data
        result = {
            'posts': enhanced_posts,
            'algorithm_scores': self._get_algorithm_debug_info(related_posts[:count]),
            'layout_type': layout_type,
            'cache_hit': False,
            'generated_at': self.post.updated_at.isoformat() if self.post.updated_at else None
        }

        # Cache the result
        cache.set(self.cache_key, result, self.CACHE_TIMEOUT)

        return result

    def get_related_by_category(self, count=4):
        """Get posts from the same categories as fallback."""
        if not self.post.categories.exists():
            return []

        cache_key = f"{self.CACHE_PREFIX}_category_{self.post.id}"
        cached = cache.get(cache_key)
        if cached:
            return cached[:count]

        from .models import Post

        # Get posts that share categories
        related = Post.objects.filter(
            categories__in=self.post.categories.all(),
            is_published=True
        ).exclude(
            id=self.post.id
        ).select_related('author').prefetch_related('categories', 'tags').annotate(
            shared_categories=Count('categories', filter=Q(categories__in=self.post.categories.all()))
        ).order_by('-shared_categories', '-created_at').distinct()[:count]

        enhanced = self._enhance_posts_metadata(list(related))
        cache.set(cache_key, enhanced, self.CACHE_TIMEOUT // 2)  # Shorter cache for fallbacks

        return enhanced

    def get_more_from_author(self, count=3):
        """Get more posts from the same author."""
        cache_key = f"{self.CACHE_PREFIX}_author_{self.post.id}"
        cached = cache.get(cache_key)
        if cached:
            return cached[:count]

        from .models import Post

        more_posts = Post.objects.filter(
            author=self.post.author,
            is_published=True
        ).exclude(
            id=self.post.id
        ).select_related('author').prefetch_related('categories', 'tags').order_by('-created_at')[:count]

        enhanced = self._enhance_posts_metadata(list(more_posts))
        cache.set(cache_key, enhanced, self.CACHE_TIMEOUT // 2)

        return enhanced

    def _calculate_related_posts(self, count):
        """Calculate related posts using weighted algorithm."""
        from .models import Post

        # Get candidate posts (published, not current post)
        candidates = Post.objects.filter(
            is_published=True
        ).exclude(
            id=self.post.id
        ).prefetch_related('tags', 'categories').select_related('author')

        # Calculate similarity scores for each candidate
        scored_posts = []
        current_content_words = self._extract_content_words(self.post.content)
        current_tags = set(self.post.tags.values_list('name', flat=True))
        current_categories = set(self.post.categories.values_list('name', flat=True))

        for candidate in candidates:
            # Calculate individual similarity scores
            scores = {
                'content_similarity': self._calculate_content_similarity(
                    current_content_words,
                    self._extract_content_words(candidate.content)
                ),
                'tag_similarity': self._calculate_tag_similarity(
                    current_tags,
                    set(candidate.tags.values_list('name', flat=True))
                ),
                'category_similarity': self._calculate_category_similarity(
                    current_categories,
                    set(candidate.categories.values_list('name', flat=True))
                ),
                'author_similarity': 1.0 if candidate.author == self.post.author else 0.0,
                'temporal_proximity': self._calculate_temporal_proximity(candidate)
            }

            # Calculate weighted total score
            total_score = sum(
                scores[factor] * self.WEIGHTS[factor]
                for factor in self.WEIGHTS
            )

            scored_posts.append({
                'post': candidate,
                'total_score': total_score,
                'individual_scores': scores
            })

        # Sort by score and return top results
        scored_posts.sort(key=lambda x: x['total_score'], reverse=True)
        return scored_posts[:count]

    def _calculate_content_similarity(self, words1, words2):
        """Calculate content similarity using word overlap and frequency."""
        if not words1 or not words2:
            return 0.0

        # Calculate word frequency for both texts
        freq1 = defaultdict(int)
        freq2 = defaultdict(int)

        for word in words1:
            freq1[word] += 1
        for word in words2:
            freq2[word] += 1

        # Calculate similarity using cosine similarity approach
        common_words = set(freq1.keys()) & set(freq2.keys())
        if not common_words:
            return 0.0

        # Calculate dot product and magnitudes
        dot_product = sum(freq1[word] * freq2[word] for word in common_words)
        magnitude1 = sum(freq**2 for freq in freq1.values()) ** 0.5
        magnitude2 = sum(freq**2 for freq in freq2.values()) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _calculate_tag_similarity(self, tags1, tags2):
        """Calculate tag similarity with higher weight for exact matches."""
        if not tags1 or not tags2:
            return 0.0

        intersection = tags1 & tags2
        union = tags1 | tags2

        if not union:
            return 0.0

        # Jaccard similarity with bonus for multiple matches
        jaccard = len(intersection) / len(union)
        match_bonus = min(len(intersection) * 0.1, 0.3)  # Up to 30% bonus

        return min(jaccard + match_bonus, 1.0)

    def _calculate_category_similarity(self, cats1, cats2):
        """Calculate category similarity."""
        if not cats1 or not cats2:
            return 0.0

        intersection = cats1 & cats2
        union = cats1 | cats2

        return len(intersection) / len(union) if union else 0.0

    def _calculate_temporal_proximity(self, candidate_post):
        """Calculate temporal proximity score (recent posts get slight boost)."""
        if not self.post.created_at or not candidate_post.created_at:
            return 0.0

        # Calculate days difference
        time_diff = abs((self.post.created_at - candidate_post.created_at).days)

        # Score decreases with time, but caps at reasonable values
        if time_diff <= 7:
            return 1.0  # Same week
        elif time_diff <= 30:
            return 0.7  # Same month
        elif time_diff <= 90:
            return 0.4  # Same quarter
        else:
            return 0.1  # Older posts

    def _extract_content_words(self, content):
        """Extract meaningful words from content for similarity analysis."""
        if not content:
            return []

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', content)

        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Remove common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'under', 'within',
            'this', 'that', 'these', 'those', 'his', 'her', 'its', 'our', 'your',
            'their', 'you', 'they', 'them', 'are', 'was', 'were', 'been', 'have',
            'has', 'had', 'will', 'would', 'could', 'should', 'may', 'might',
            'can', 'must', 'shall', 'not', 'yes', 'all', 'any', 'both', 'each',
            'few', 'more', 'most', 'other', 'some', 'such', 'than', 'too', 'very'
        }

        # Filter out stop words and short words
        meaningful_words = [word for word in words if word not in stop_words and len(word) >= 3]

        return meaningful_words

    def _enhance_posts_metadata(self, scored_posts):
        """Add metadata to posts for display purposes."""
        enhanced = []

        for item in scored_posts:
            post = item['post'] if isinstance(item, dict) and 'post' in item else item

            # Determine engagement hints
            engagement_hints = self._get_engagement_hints(post)

            # Calculate reading progress context
            reading_context = self._get_reading_context(post)

            enhanced_post = {
                'post': post,
                'reading_time': post.get_reading_time(),
                'engagement_hints': engagement_hints,
                'reading_context': reading_context,
                'similarity_score': item.get('total_score', 0) if isinstance(item, dict) else 0,
                'primary_category': post.categories.first(),
                'tag_count': post.tags.count(),
                'is_recent': (timezone.now() - post.created_at).days <= 7 if post.created_at else False,
                'share_popularity': post.total_shares,
            }

            enhanced.append(enhanced_post)

        return enhanced

    def _get_engagement_hints(self, post):
        """Generate engagement hints based on post characteristics."""
        hints = []

        # Reading time hints
        reading_time = post.get_reading_time()
        if reading_time <= 3:
            hints.append("Quick read")
        elif reading_time <= 7:
            hints.append("Medium read")
        else:
            hints.append("In-depth read")

        # Popularity hints
        if post.total_shares > 10:
            hints.append("Popular")
        elif post.total_shares > 5:
            hints.append("Well-shared")

        # Freshness hints
        if hasattr(post, 'created_at') and post.created_at:
            from django.utils import timezone
            days_old = (timezone.now() - post.created_at).days
            if days_old <= 7:
                hints.append("Recent")
            elif days_old <= 30:
                hints.append("This month")

        # Content type hints based on categories
        categories = list(post.categories.all())
        if categories:
            category_names = [cat.name.lower() for cat in categories]
            if any(name in ['tutorial', 'guide', 'how-to'] for name in category_names):
                hints.append("Tutorial")
            elif any(name in ['review', 'comparison'] for name in category_names):
                hints.append("Review")
            elif any(name in ['news', 'update'] for name in category_names):
                hints.append("News")

        return hints[:3]  # Limit to 3 most relevant hints

    def _get_reading_context(self, post):
        """Generate reading context suggestions."""
        contexts = []

        # Content difficulty
        content_length = len(post.content) if post.content else 0
        if content_length > 5000:
            contexts.append("Comprehensive guide")
        elif content_length > 2000:
            contexts.append("Detailed article")
        else:
            contexts.append("Focused topic")

        # Best reading time
        reading_time = post.get_reading_time()
        if reading_time <= 2:
            contexts.append("Perfect for a coffee break")
        elif reading_time <= 5:
            contexts.append("Great for commute reading")
        else:
            contexts.append("Set aside some time")

        return contexts

    def _get_algorithm_debug_info(self, scored_posts):
        """Get debug information about how scores were calculated."""
        if not getattr(settings, 'DEBUG', False):
            return None  # Only provide debug info in debug mode

        debug_info = []
        for item in scored_posts:
            if isinstance(item, dict) and 'individual_scores' in item:
                debug_info.append({
                    'post_title': item['post'].title,
                    'total_score': round(item['total_score'], 3),
                    'scores': {k: round(v, 3) for k, v in item['individual_scores'].items()}
                })

        return debug_info

    def _generate_cache_key(self):
        """Generate a unique cache key for this post's related posts."""
        # Include post ID, update time, and algorithm version for cache invalidation
        key_data = f"{self.post.id}_{self.post.updated_at.timestamp() if self.post.updated_at else 0}_v2"
        return f"{self.CACHE_PREFIX}_{hashlib.md5(key_data.encode()).hexdigest()}"

    @classmethod
    def invalidate_cache_for_post(cls, post_id):
        """Invalidate related posts cache when a post is updated."""
        # This would be called from post save signals
        pattern = f"{cls.CACHE_PREFIX}_*"
        # Note: Django's default cache doesn't support pattern deletion
        # This could be enhanced with Redis cache backend for better performance
        logger.info(f"Cache invalidation requested for post {post_id}")

    @classmethod
    def warm_cache_for_popular_posts(cls):
        """Pre-warm cache for popular/featured posts."""
        from .models import Post

        popular_posts = Post.objects.filter(
            is_published=True,
            is_featured=True
        ).order_by('-total_shares', '-created_at')[:10]

        warmed_count = 0
        for post in popular_posts:
            service = cls(post)
            service.get_related_posts()  # This will cache the results
            warmed_count += 1

        logger.info(f"Cache warmed for {warmed_count} popular posts")
        return warmed_count