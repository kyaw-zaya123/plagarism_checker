document.addEventListener('DOMContentLoaded', function () {
    const numFilesInput = document.getElementById('num_files');
    const fileInputsContainer = document.getElementById('file_inputs');
    const form = document.querySelector('form');

    /**
     * Creates a file input element dynamically.
     * @param {number} index - The index of the file input.
     * @returns {HTMLDivElement} - The container div with the file input and label.
     */
    function createFileInput(index) {
        const div = document.createElement('div');
        div.className = 'form-group';

        const label = document.createElement('label');
        label.textContent = `Файл ${index + 1}:`;
        label.htmlFor = `file_${index + 1}`;

        const input = document.createElement('input');
        input.type = 'file';
        input.id = `file_${index + 1}`;
        input.name = `file_${index + 1}`;
        input.required = true;

        div.appendChild(label);
        div.appendChild(input);
        return div;
    }

    /**
     * Updates the file input elements based on the number of files specified.
     */
    function updateFileInputs() {
        const numFiles = parseInt(numFilesInput.value, 10) || 0;
        fileInputsContainer.innerHTML = ''; // Clear existing inputs

        for (let i = 0; i < numFiles; i++) {
            fileInputsContainer.appendChild(createFileInput(i));
        }
    }

    // Initialize file inputs and attach event listener to number input
    updateFileInputs();
    numFilesInput.addEventListener('input', updateFileInputs);

    /**
     * Validates the form to ensure all file inputs are selected before submission.
     * Displays an error if any file is missing.
     */
    form.addEventListener('submit', function (event) {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        let allFilesSelected = true;

        fileInputs.forEach(input => {
            if (!input.files.length) {
                allFilesSelected = false;
                input.classList.add('error'); // Highlight missing file input
            } else {
                input.classList.remove('error'); // Remove error highlight
            }
        });

        if (!allFilesSelected) {
            event.preventDefault(); // Prevent form submission
            alert('Пожалуйста, выберите все необходимые файлы.');
        }
    });

    /**
     * Validates the file type for each file input to ensure it matches the allowed formats.
     */
    fileInputsContainer.addEventListener('change', function (event) {
        if (event.target.type === 'file') {
            const file = event.target.files[0];
            const allowedTypes = [
                'text/plain',
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/html'
            ];

            if (file && !allowedTypes.includes(file.type)) {
                event.target.value = ''; // Clear invalid file input
                alert('Пожалуйста, выберите файл в формате .txt, .pdf, .docx или .html');
            }
        }
    });

    /**
     * Handles the confirmation modal for file deletion with an API call.
     * @param {string} id - The ID of the item to delete.
     */
    window.confirmDelete = function (id) {
        const deleteForm = document.getElementById('deleteForm');
        deleteForm.action = `/delete/${id}`;
        $('#deleteConfirmModal').modal('show');

                
                fetch(`/api/delete/${id}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${yourAuthToken}` // Add your auth token here
                    }
                })
                .then(response => {
                    if (response.status === 401) {
                        window.location.href = '/login';  // Redirect to login page if unauthorized
                        return;
                    }
                    return response.json();
                })
                .then(data => {
                    if (data) {
                        console.log(data);
                        // Handle success/error
                        alert(data.message || 'Item deleted successfully!');
                        location.reload(); // Optionally refresh the page
                    }
                })
                .catch(error => console.error('Error:', error));
            };
    /**
     * Handles delete button click inside the modal, submitting the form.
     */
    const deleteButton = document.querySelector('#deleteConfirmModal .btn-danger');
    if (deleteButton) {
        deleteButton.addEventListener('click', function () {
            document.getElementById('deleteForm').submit();
        });
    }
});
