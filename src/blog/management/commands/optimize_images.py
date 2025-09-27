"""
Management command to optimize blog images using the enhanced image processor.
Provides testing and batch processing capabilities for image optimization.
"""
import os
import time
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from blog.models import Post
from blog.image_utils_enhanced import (
    ImageProcessor,
    get_image_metadata,
    AltTextManager,
    ImageCDNOptimizer
)
from blog.signals import cleanup_orphaned_files, get_storage_stats, format_file_size


class Command(BaseCommand):
    help = 'Optimize blog images with WebP conversion, responsive sizing, and compression'

    def add_arguments(self, parser):
        parser.add_argument(
            '--post-id',
            type=int,
            help='Optimize images for a specific post ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Optimize images for all posts with featured images',
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Run optimization tests on existing images',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show image optimization statistics',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up all orphaned files (images and attachments)',
        )
        parser.add_argument(
            '--storage-stats',
            action='store_true',
            help='Show detailed storage usage statistics',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually processing',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing of already optimized images',
        )
        parser.add_argument(
            '--format',
            choices=['json', 'table'],
            default='table',
            help='Output format for stats and results',
        )

    def handle(self, *args, **options):
        if options['test']:
            self.run_tests()
        elif options['stats']:
            self.show_stats(options['format'])
        elif options['storage_stats']:
            self.show_storage_stats()
        elif options['cleanup']:
            self.cleanup_orphaned_images(options['dry_run'])
        elif options['post_id']:
            self.optimize_single_post(options['post_id'], options['force'], options['dry_run'])
        elif options['all']:
            self.optimize_all_posts(options['force'], options['dry_run'])
        else:
            self.stdout.write(
                self.style.ERROR('Please specify an action: --test, --stats, --cleanup, --post-id, or --all')
            )

    def run_tests(self):
        """Run comprehensive tests on the image optimization pipeline."""
        self.stdout.write(self.style.SUCCESS('🧪 Running Image Optimization Tests'))
        self.stdout.write('=' * 60)

        # Test 1: Check if required dependencies are available
        self.stdout.write('\n1. Testing Dependencies...')
        try:
            from PIL import Image, ImageOps
            self.stdout.write(self.style.SUCCESS('   ✓ PIL/Pillow available'))
        except ImportError:
            self.stdout.write(self.style.ERROR('   ✗ PIL/Pillow not available'))
            return

        # Test 2: Test WebP support
        self.stdout.write('\n2. Testing WebP Support...')
        try:
            # Create a test image
            test_img = Image.new('RGB', (100, 100), color='red')
            webp_io = ContentFile(b'', name='test.webp')

            # Try to save as WebP
            from io import BytesIO
            webp_buffer = BytesIO()
            test_img.save(webp_buffer, format='WebP', quality=80)

            self.stdout.write(self.style.SUCCESS('   ✓ WebP encoding supported'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ WebP encoding failed: {e}'))

        # Test 3: Test image processor functionality
        self.stdout.write('\n3. Testing Image Processor...')
        try:
            # Test with a sample post that has an image
            posts_with_images = Post.objects.filter(featured_image__isnull=False)[:1]

            if posts_with_images:
                post = posts_with_images.first()
                base_name = post.get_image_base_name()

                if base_name:
                    # Test metadata generation
                    metadata = get_image_metadata(base_name)
                    self.stdout.write(self.style.SUCCESS(f'   ✓ Generated metadata for {base_name}'))
                    self.stdout.write(f'      - Available formats: {metadata.get("available_formats", [])}')
                    self.stdout.write(f'      - Total variants: {metadata.get("total_variants", 0)}')
                else:
                    self.stdout.write(self.style.WARNING('   ⚠ No processed images found for testing'))
            else:
                self.stdout.write(self.style.WARNING('   ⚠ No posts with featured images found'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Image processor test failed: {e}'))

        # Test 4: Test alt text generation
        self.stdout.write('\n4. Testing Alt Text Generation...')
        try:
            test_alt = AltTextManager.generate_smart_alt(
                'test_image.jpg',
                context={'post_title': 'Test Post'},
                user_input='A beautiful landscape'
            )
            self.stdout.write(self.style.SUCCESS(f'   ✓ Generated alt text: "{test_alt}"'))

            # Test validation
            validation = AltTextManager.validate_alt_text(test_alt)
            self.stdout.write(f'   - Validation score: {validation["score"]}/100')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Alt text generation failed: {e}'))

        # Test 5: Test CDN optimizer
        self.stdout.write('\n5. Testing CDN Optimizer...')
        try:
            sizes = ImageCDNOptimizer.generate_responsive_sizes()
            self.stdout.write(self.style.SUCCESS(f'   ✓ Generated responsive sizes: {sizes}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ CDN optimizer test failed: {e}'))

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('🎉 Image optimization tests completed!'))

    def optimize_single_post(self, post_id, force=False, dry_run=False):
        """Optimize images for a single post."""
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            raise CommandError(f'Post with ID {post_id} does not exist')

        if not post.featured_image:
            self.stdout.write(self.style.WARNING(f'Post "{post.title}" has no featured image'))
            return

        self.stdout.write(f'Optimizing images for post: "{post.title}"')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No actual processing will occur'))

        base_name = post.get_image_base_name()

        # Check if already optimized
        if base_name and not force:
            metadata = get_image_metadata(base_name)
            if metadata.get('total_variants', 0) > 0:
                self.stdout.write(self.style.WARNING(
                    f'Post already has {metadata["total_variants"]} optimized variants. Use --force to reprocess.'
                ))
                return

        if not dry_run:
            start_time = time.time()

            # Process the image
            is_hero = post.is_featured
            processed_data = ImageProcessor.process_image(
                post.featured_image,
                base_name or f'post_{post.pk}_{int(time.time())}',
                is_hero=is_hero,
                generate_alt=True
            )

            processing_time = time.time() - start_time

            if processed_data:
                variants_created = len([k for k in processed_data.keys() if k.endswith(('_jpg', '_webp'))])
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Created {variants_created} image variants in {processing_time:.2f}s'
                ))

                # Show generated alt text if available
                if processed_data.get('generated_alt'):
                    self.stdout.write(f'  Generated alt text: "{processed_data["generated_alt"]}"')

                # Show CDN metadata
                cdn_metadata = processed_data.get('cdn_metadata', {})
                if cdn_metadata:
                    self.stdout.write(f'  Available formats: {cdn_metadata.get("formats", [])}')
                    self.stdout.write(f'  Preload hints: {len(cdn_metadata.get("preload_hints", []))}')
            else:
                self.stdout.write(self.style.ERROR('✗ Image processing failed'))
        else:
            self.stdout.write(f'Would process: {post.featured_image.name}')
            self.stdout.write(f'Is hero image: {post.is_featured}')

    def optimize_all_posts(self, force=False, dry_run=False):
        """Optimize images for all posts with featured images."""
        posts = Post.objects.filter(featured_image__isnull=False)
        total_posts = posts.count()

        if total_posts == 0:
            self.stdout.write(self.style.WARNING('No posts with featured images found'))
            return

        self.stdout.write(f'Found {total_posts} posts with featured images')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No actual processing will occur'))

        processed_count = 0
        skipped_count = 0
        failed_count = 0
        total_processing_time = 0

        for i, post in enumerate(posts, 1):
            self.stdout.write(f'\n[{i}/{total_posts}] Processing: "{post.title}"')

            base_name = post.get_image_base_name()

            # Check if already optimized
            if base_name and not force:
                metadata = get_image_metadata(base_name)
                if metadata.get('total_variants', 0) > 0:
                    self.stdout.write(self.style.WARNING(f'  Skipped - already has {metadata["total_variants"]} variants'))
                    skipped_count += 1
                    continue

            if not dry_run:
                try:
                    start_time = time.time()

                    is_hero = post.is_featured
                    processed_data = ImageProcessor.process_image(
                        post.featured_image,
                        base_name or f'post_{post.pk}_{int(time.time())}',
                        is_hero=is_hero,
                        generate_alt=True
                    )

                    processing_time = time.time() - start_time
                    total_processing_time += processing_time

                    if processed_data:
                        variants_created = len([k for k in processed_data.keys() if k.endswith(('_jpg', '_webp'))])
                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓ Created {variants_created} variants in {processing_time:.2f}s'
                        ))
                        processed_count += 1
                    else:
                        self.stdout.write(self.style.ERROR('  ✗ Processing failed'))
                        failed_count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Error: {e}'))
                    failed_count += 1
            else:
                self.stdout.write(f'  Would process: {post.featured_image.name}')

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('OPTIMIZATION SUMMARY:'))
        self.stdout.write(f'  Processed: {processed_count}')
        self.stdout.write(f'  Skipped: {skipped_count}')
        self.stdout.write(f'  Failed: {failed_count}')

        if total_processing_time > 0:
            self.stdout.write(f'  Total time: {total_processing_time:.2f}s')
            self.stdout.write(f'  Average time per image: {total_processing_time/max(processed_count, 1):.2f}s')

    def show_stats(self, output_format='table'):
        """Show comprehensive image optimization statistics."""
        posts_with_images = Post.objects.filter(featured_image__isnull=False)
        total_posts = posts_with_images.count()

        if total_posts == 0:
            self.stdout.write(self.style.WARNING('No posts with featured images found'))
            return

        stats = {
            'total_posts': total_posts,
            'optimized_posts': 0,
            'total_variants': 0,
            'webp_variants': 0,
            'jpg_variants': 0,
            'hero_images': 0,
            'sizes_breakdown': {},
            'optimization_coverage': 0.0
        }

        for post in posts_with_images:
            base_name = post.get_image_base_name()
            if base_name:
                metadata = get_image_metadata(base_name)
                if metadata.get('total_variants', 0) > 0:
                    stats['optimized_posts'] += 1
                    stats['total_variants'] += metadata['total_variants']

                    # Count formats
                    if 'webp' in metadata.get('available_formats', []):
                        stats['webp_variants'] += len([s for s in metadata['available_sizes'] if 'webp' in s.get('formats', [])])
                    if 'jpg' in metadata.get('available_formats', []):
                        stats['jpg_variants'] += len([s for s in metadata['available_sizes'] if 'jpg' in s.get('formats', [])])

                    # Count hero images
                    if any('hero_' in s['name'] for s in metadata['available_sizes']):
                        stats['hero_images'] += 1

                    # Size breakdown
                    for size_data in metadata['available_sizes']:
                        size_name = size_data['name']
                        if size_name not in stats['sizes_breakdown']:
                            stats['sizes_breakdown'][size_name] = 0
                        stats['sizes_breakdown'][size_name] += 1

        stats['optimization_coverage'] = (stats['optimized_posts'] / total_posts) * 100 if total_posts > 0 else 0

        if output_format == 'json':
            import json
            self.stdout.write(json.dumps(stats, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS('📊 IMAGE OPTIMIZATION STATISTICS'))
            self.stdout.write('=' * 60)
            self.stdout.write(f'Total posts with images: {stats["total_posts"]}')
            self.stdout.write(f'Optimized posts: {stats["optimized_posts"]}')
            self.stdout.write(f'Optimization coverage: {stats["optimization_coverage"]:.1f}%')
            self.stdout.write(f'Total image variants: {stats["total_variants"]}')
            self.stdout.write(f'WebP variants: {stats["webp_variants"]}')
            self.stdout.write(f'JPEG variants: {stats["jpg_variants"]}')
            self.stdout.write(f'Hero images: {stats["hero_images"]}')

            if stats['sizes_breakdown']:
                self.stdout.write('\nSize Distribution:')
                for size, count in sorted(stats['sizes_breakdown'].items()):
                    self.stdout.write(f'  {size}: {count}')

            # Add storage statistics
            self.stdout.write('\n' + '=' * 60)
            storage_stats = get_storage_stats()
            self.stdout.write(self.style.SUCCESS('💾 STORAGE STATISTICS'))
            self.stdout.write('=' * 60)

            self.stdout.write(f'Featured Images: {storage_stats["featured_images"]["count"]} files ({format_file_size(storage_stats["featured_images"]["size"])})')
            self.stdout.write(f'Processed Images: {storage_stats["processed_images"]["count"]} files ({format_file_size(storage_stats["processed_images"]["size"])})')
            self.stdout.write(f'Blog Files: {storage_stats["blog_files"]["count"]} files ({format_file_size(storage_stats["blog_files"]["size"])})')
            self.stdout.write(f'Total Storage Used: {format_file_size(storage_stats["total_size"])}')

    def show_storage_stats(self):
        """Show detailed storage usage statistics."""
        self.stdout.write(self.style.SUCCESS('💾 DETAILED STORAGE STATISTICS'))
        self.stdout.write('=' * 60)

        try:
            storage_stats = get_storage_stats()

            # Featured Images
            self.stdout.write('\n📸 Featured Images:')
            self.stdout.write(f'  Count: {storage_stats["featured_images"]["count"]} files')
            self.stdout.write(f'  Size: {format_file_size(storage_stats["featured_images"]["size"])}')

            # Processed Images
            self.stdout.write('\n🔄 Processed Images:')
            self.stdout.write(f'  Count: {storage_stats["processed_images"]["count"]} files')
            self.stdout.write(f'  Size: {format_file_size(storage_stats["processed_images"]["size"])}')

            # Blog Files
            self.stdout.write('\n📎 Blog Attachments:')
            self.stdout.write(f'  Count: {storage_stats["blog_files"]["count"]} files')
            self.stdout.write(f'  Size: {format_file_size(storage_stats["blog_files"]["size"])}')

            # Total
            self.stdout.write('\n📊 Total Usage:')
            self.stdout.write(f'  Total Files: {sum([storage_stats[key]["count"] for key in ["featured_images", "processed_images", "blog_files"]])}')
            self.stdout.write(f'  Total Size: {format_file_size(storage_stats["total_size"])}')

            # Calculate optimization ratio
            if storage_stats["featured_images"]["count"] > 0:
                optimization_ratio = storage_stats["processed_images"]["count"] / storage_stats["featured_images"]["count"]
                self.stdout.write(f'  Optimization Ratio: {optimization_ratio:.1f}x (processed images per original)')

            # Storage efficiency
            if storage_stats["total_size"] > 0:
                featured_percentage = (storage_stats["featured_images"]["size"] / storage_stats["total_size"]) * 100
                processed_percentage = (storage_stats["processed_images"]["size"] / storage_stats["total_size"]) * 100
                files_percentage = (storage_stats["blog_files"]["size"] / storage_stats["total_size"]) * 100

                self.stdout.write('\n📈 Storage Distribution:')
                self.stdout.write(f'  Featured Images: {featured_percentage:.1f}%')
                self.stdout.write(f'  Processed Images: {processed_percentage:.1f}%')
                self.stdout.write(f'  Blog Files: {files_percentage:.1f}%')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error getting storage statistics: {e}'))

    def cleanup_orphaned_images(self, dry_run=False):
        """Clean up all orphaned files (images and attachments)."""
        self.stdout.write('🧹 Cleaning up orphaned files...')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No files will be deleted'))

            # For dry run, we'll simulate the cleanup
            posts_with_images = Post.objects.filter(featured_image__isnull=False)
            total_posts = posts_with_images.count()

            self.stdout.write(f'Found {total_posts} posts with featured images')

            # Check featured images directory
            try:
                if default_storage.exists('blog/images/'):
                    dirs, files = default_storage.listdir('blog/images/')
                    self.stdout.write(f'Found {len(files)} files in blog/images/ directory')

                    # Count potentially orphaned files
                    used_images = set()
                    for post in posts_with_images:
                        if post.featured_image:
                            used_images.add(post.featured_image.name)

                    orphaned_featured = [f for f in files if f'blog/images/{f}' not in used_images]
                    self.stdout.write(f'Would delete {len(orphaned_featured)} orphaned featured images')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error checking featured images: {e}'))

            # Check processed images directory
            try:
                if default_storage.exists('blog/images/processed/'):
                    dirs, files = default_storage.listdir('blog/images/processed/')
                    self.stdout.write(f'Found {len(files)} processed image files')

                    # Count potentially orphaned processed files
                    valid_base_names = set()
                    for post in posts_with_images:
                        base_name = post.get_image_base_name()
                        if base_name:
                            valid_base_names.add(base_name)

                    orphaned_processed = []
                    for filename in files:
                        name_parts = filename.rsplit('_', 1)
                        if len(name_parts) == 2 and name_parts[0] not in valid_base_names:
                            orphaned_processed.append(filename)

                    self.stdout.write(f'Would delete {len(orphaned_processed)} orphaned processed images')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error checking processed images: {e}'))

            return

        # Actually perform cleanup
        try:
            orphaned_count = cleanup_orphaned_files()
            if orphaned_count > 0:
                self.stdout.write(self.style.SUCCESS(f'✓ Cleaned up {orphaned_count} orphaned files'))
            else:
                self.stdout.write(self.style.SUCCESS('✓ No orphaned files found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during cleanup: {e}'))