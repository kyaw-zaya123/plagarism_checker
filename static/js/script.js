// for upload.html
document.addEventListener('DOMContentLoaded', function() {
    const MAX_FILES = 10;
    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB in bytes
    const ALLOWED_TYPES = ['.pdf', '.docx', '.txt'];
    
    const form = document.getElementById('file-comparison-form');
    const container = document.getElementById('file-upload-container');
    const addButton = document.getElementById('add-file');
    const removeButton = document.getElementById('remove-file');
    const compareButton = document.getElementById('compare-button');
    
    let fileUploadCount = 1;

    // Utility Functions
    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const validateFile = (file) => {
        const errors = [];
        
        if (!file) return errors;
        
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!ALLOWED_TYPES.includes(extension)) {
            errors.push(`Invalid file type. Allowed types: ${ALLOWED_TYPES.join(', ')}`);
        }
        
        if (file.size > MAX_FILE_SIZE) {
            errors.push(`File size exceeds ${formatFileSize(MAX_FILE_SIZE)}`);
        }
        
        return errors;
    };

    const createFileInput = (index) => {
        const div = document.createElement('div');
        div.classList.add('mb-4', 'file-upload');
        
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <label for="file-upload-${index}" class="form-label h5 mb-0">
                    <span class="fas fa-file-alt me-2" aria-hidden="true"></span>
                    File ${index}
                </label>
                <span class="badge bg-secondary" id="file-size-${index}"></span>
            </div>
            <input type="file" 
                   id="file-upload-${index}" 
                   name="files" 
                   class="form-control form-control-lg"
                   accept=".pdf,.docx,.txt"
                   aria-describedby="file-help-${index}"
                   required>
            <div class="invalid-feedback">Please select a valid file.</div>
            <div id="file-help-${index}" class="form-text">
            </div>
        `;
        
        return div;
    };

    // Event Handlers
    const handleFileChange = (event) => {
        const input = event.target;
        const sizeLabel = document.getElementById(`file-size-${input.id.split('-').pop()}`);
        const file = input.files[0];
        
        if (file) {
            const errors = validateFile(file);
            
            if (errors.length > 0) {
                input.value = '';
                sizeLabel.textContent = '';
                alert(errors.join('\n'));
            } else {
                sizeLabel.textContent = formatFileSize(file.size);
            }
        } else {
            sizeLabel.textContent = '';
        }
        
        updateFormState();
    };

    const updateFormState = () => {
        const fileInputs = container.querySelectorAll('input[type="file"]');
        const hasFiles = Array.from(fileInputs).some(input => input.files.length > 0);
        
        removeButton.disabled = fileUploadCount === 1;
        addButton.disabled = fileUploadCount === MAX_FILES;
        compareButton.disabled = !hasFiles;
    };

    // Event Listeners
    addButton.addEventListener('click', () => {
        if (fileUploadCount < MAX_FILES) {
            fileUploadCount++;
            const newInput = createFileInput(fileUploadCount);
            container.appendChild(newInput);
            
            const fileInput = newInput.querySelector('input[type="file"]');
            fileInput.addEventListener('change', handleFileChange);
            
            updateFormState();
        }
    });

    removeButton.addEventListener('click', () => {
        if (fileUploadCount > 1) {
            container.removeChild(container.lastElementChild);
            fileUploadCount--;
            updateFormState();
        }
    });

    // Form validation
    form.addEventListener('submit', (event) => {
        if (!form.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        form.classList.add('was-validated');
    });

    // Initialize event listeners for existing file input
    document.querySelector('input[type="file"]').addEventListener('change', handleFileChange);
    updateFormState();
});


//for register.html
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.password-toggle').forEach(toggle => {
        toggle.addEventListener('click', function() {
            let input = this.previousElementSibling;
            let icon = this.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.replace('fa-eye', 'fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.replace('fa-eye-slash', 'fa-eye');
            }
        });
    });
});


// for login.html
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.password-toggle').forEach(toggle => {
        toggle.addEventListener('click', function() {
            let input = this.previousElementSibling;
            let icon = this.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.replace('fa-eye', 'fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.replace('fa-eye-slash', 'fa-eye');
            }
        });
    });
});