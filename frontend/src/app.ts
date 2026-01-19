// Type definitions
interface ProcessLectureResponse {
    success: boolean;
    message: string;
    data: {
        slide_data: {
            [key: string]: {
                slide_number: number;
                content: string;
                transcripts: string[];
            };
        };
        parameters: {
            window_size: number;
            similarity_threshold: number;
        };
    };
}

// Configuration
const API_URL = 'http://localhost:8000';

// DOM Elements
const uploadForm = document.getElementById('uploadForm') as HTMLFormElement;
const pdfFileInput = document.getElementById('pdfFile') as HTMLInputElement;
const transcriptFileInput = document.getElementById('transcriptFile') as HTMLInputElement;
const pdfFileInfo = document.getElementById('pdfFileInfo') as HTMLSpanElement;
const transcriptFileInfo = document.getElementById('transcriptFileInfo') as HTMLSpanElement;
const submitBtn = document.getElementById('submitBtn') as HTMLButtonElement;
const windowSizeInput = document.getElementById('windowSize') as HTMLInputElement;
const similarityThresholdInput = document.getElementById('similarityThreshold') as HTMLInputElement;

const progressSection = document.getElementById('progressSection') as HTMLDivElement;
const progressBar = document.getElementById('progressBar') as HTMLDivElement;
const progressText = document.getElementById('progressText') as HTMLParagraphElement;

const resultsSection = document.getElementById('resultsSection') as HTMLDivElement;
const statsGrid = document.getElementById('statsGrid') as HTMLDivElement;
const downloadBtn = document.getElementById('downloadBtn') as HTMLButtonElement;
const resetBtn = document.getElementById('resetBtn') as HTMLButtonElement;

const errorSection = document.getElementById('errorSection') as HTMLDivElement;
const errorText = document.getElementById('errorText') as HTMLParagraphElement;
const errorResetBtn = document.getElementById('errorResetBtn') as HTMLButtonElement;

// Store the API response for download
let apiResponse: ProcessLectureResponse | null = null;

// File input change handlers
pdfFileInput.addEventListener('change', (e) => {
    const target = e.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
        pdfFileInfo.textContent = target.files[0].name;
    } else {
        pdfFileInfo.textContent = 'No file chosen';
    }
});

transcriptFileInput.addEventListener('change', (e) => {
    const target = e.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
        transcriptFileInfo.textContent = target.files[0].name;
    } else {
        transcriptFileInfo.textContent = 'No file chosen';
    }
});

// Form submission handler
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Validate files
    if (!pdfFileInput.files || pdfFileInput.files.length === 0) {
        showError('Please select a PDF file');
        return;
    }
    
    if (!transcriptFileInput.files || transcriptFileInput.files.length === 0) {
        showError('Please select a transcript file');
        return;
    }
    
    // Prepare form data
    const formData = new FormData();
    formData.append('pdf_file', pdfFileInput.files[0]);
    formData.append('transcript_file', transcriptFileInput.files[0]);
    formData.append('window_size', windowSizeInput.value);
    formData.append('similarity_threshold', similarityThresholdInput.value);
    
    // Show progress
    showProgress();
    
    try {
        const response = await fetch(`${API_URL}/process-lecture`, {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const data: ProcessLectureResponse = await response.json();
        apiResponse = data;
        
        // Show results
        showResults(data);
        
    } catch (error) {
        console.error('Error processing lecture:', error);
        showError(error instanceof Error ? error.message : 'An unexpected error occurred');
    }
});

// Download handler function
function downloadResults(): void {
    if (!apiResponse) {
        showError('No data available to download');
        return;
    }
    
    // Create a blob from the JSON data
    const jsonString = JSON.stringify(apiResponse, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    
    // Create download link
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lecture-results-${new Date().getTime()}.json`;
    document.body.appendChild(a);
    a.click();
    
    // Cleanup
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Initial button handlers (will be overridden when results are shown)
if (resetBtn) resetBtn.addEventListener('click', resetForm);
if (errorResetBtn) errorResetBtn.addEventListener('click', resetForm);

// UI state functions
function showProgress(): void {
    uploadForm.parentElement!.style.display = 'none';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';
    progressSection.style.display = 'block';
    
    // Animate progress bar
    progressBar.style.width = '0%';
    setTimeout(() => {
        progressBar.style.width = '90%';
    }, 100);
    
    progressText.textContent = 'Processing your lecture files...';
    submitBtn.disabled = true;
}

function showResults(data: ProcessLectureResponse): void {
    // Hide all other sections
    uploadForm.parentElement!.style.display = 'none';
    errorSection.style.display = 'none';
    progressSection.style.display = 'none';
    
    // Reset progress bar
    progressBar.style.width = '0%';
    
    // Show results
    resultsSection.style.display = 'block';
    resultsSection.innerHTML = ''; // Clear previous results
    
    // Add title
    const titleElement = document.createElement('h2');
    titleElement.textContent = 'Processing Complete';
    resultsSection.appendChild(titleElement);
    
    // Add success message from backend
    const messageElement = document.createElement('p');
    messageElement.className = 'success-message';
    messageElement.textContent = data.message || 'Your lecture has been processed successfully. You can now download the results as JSON.';
    resultsSection.appendChild(messageElement);
    
    // Add info about data
    const infoElement = document.createElement('p');
    infoElement.className = 'info-message';
    const slideCount = Object.keys(data.data.slide_data || {}).length;
    infoElement.textContent = `The results contain ${slideCount} slide(s). Click below to download the complete data.`;
    resultsSection.appendChild(infoElement);
    
    // Add action buttons
    const actionButtons = document.createElement('div');
    actionButtons.className = 'action-buttons';
    actionButtons.innerHTML = `
        <button id="downloadBtn" class="download-btn">Download JSON Results</button>
        <button id="resetBtn" class="reset-btn">Process Another File</button>
    `;
    resultsSection.appendChild(actionButtons);
    
    // Re-attach event listeners for buttons
    const downloadButton = document.getElementById('downloadBtn') as HTMLButtonElement;
    const resetButton = document.getElementById('resetBtn') as HTMLButtonElement;
    downloadButton.addEventListener('click', downloadResults);
    resetButton.addEventListener('click', resetForm);
}

function showError(message: string): void {
    uploadForm.parentElement!.style.display = 'none';
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'block';
    
    errorText.textContent = message;
    submitBtn.disabled = false;
}

function resetForm(): void {
    // Reset form inputs
    uploadForm.reset();
    pdfFileInfo.textContent = 'No file chosen';
    transcriptFileInfo.textContent = 'No file chosen';
    
    // Reset UI state
    uploadForm.parentElement!.style.display = 'block';
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';
    
    // Reset stored data
    apiResponse = null;
    submitBtn.disabled = false;
}

// Initialize
console.log('PDF Lecture Parser Frontend loaded');
console.log(`API URL: ${API_URL}`);
