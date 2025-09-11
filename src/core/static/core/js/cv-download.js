/**
 * CV Download functionality
 * Handles bilingual CV printing without URL parameters
 */

async function downloadCV(lang) {
    try {
        // Fetch the CV content in the desired language
        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.set('pdf_lang', lang);
        
        const response = await fetch(currentUrl.toString());
        const html = await response.text();
        
        // Parse the response to get just the CV content
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newCvContent = doc.querySelector('.cv-markdown-content');
        
        if (newCvContent) {
            // Store original content
            const originalContent = document.querySelector('.cv-markdown-content').innerHTML;
            
            // Replace current content temporarily
            document.querySelector('.cv-markdown-content').innerHTML = newCvContent.innerHTML;
            
            // Trigger print
            window.print();
            
            // Restore original content after print
            setTimeout(function() {
                document.querySelector('.cv-markdown-content').innerHTML = originalContent;
            }, 100);
        } else {
            // Fallback: just print current page
            window.print();
        }
    } catch (error) {
        console.error('Error downloading CV:', error);
        // Fallback: just print current page
        window.print();
    }
}