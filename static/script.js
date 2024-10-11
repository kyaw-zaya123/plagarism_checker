document.addEventListener('DOMContentLoaded', function () {
    const numFilesInput = document.getElementById('num_files');
    const fileInputsContainer = document.getElementById('file_inputs');

    // Function to update the file inputs dynamically based on the number entered
    function updateFileInputs() {
        const numFiles = parseInt(numFilesInput.value, 10);
        fileInputsContainer.innerHTML = '';  // Clear previous inputs

        for (let i = 0; i < numFiles; i++) {
            const div = document.createElement('div');
            div.className = 'form-group';
            
            const label = document.createElement('label');
            label.textContent = `Файл ${i + 1}:`;
            label.htmlFor = `file_${i + 1}`;

            const input = document.createElement('input');
            input.type = 'file';
            input.id = `file_${i + 1}`;
            input.name = `file_${i + 1}`;
            input.required = true;

            div.appendChild(label);
            div.appendChild(input);
            fileInputsContainer.appendChild(div);
        }
    }

    // Attach event listener to update file inputs whenever the number changes
    numFilesInput.addEventListener('input', updateFileInputs);

    // Initial call to set up file inputs based on the default value
    updateFileInputs();

    // Add form validation to ensure all files are selected before submitting the form
    const form = document.querySelector('form');
    form.addEventListener('submit', function (event) {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        let allFilesSelected = true;

        // Check if all file inputs have a selected file
        fileInputs.forEach(input => {
            if (!input.files.length) {
                allFilesSelected = false;
                input.classList.add('error');
            } else {
                input.classList.remove('error');
            }
        });

        if (!allFilesSelected) {
            event.preventDefault();  // Prevent form submission if not all files are selected
            alert('Пожалуйста, выберите все необходимые файлы.');
        }
    });

    // Add file type validation for allowed formats
    fileInputsContainer.addEventListener('change', function (event) {
        if (event.target.type === 'file') {
            const file = event.target.files[0];
            const allowedTypes = ['text/plain', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/html'];

            // Check if the selected file type is allowed
            if (file && !allowedTypes.includes(file.type)) {
                event.target.value = '';  // Clear the file input if the type is not allowed
                alert('Пожалуйста, выберите файл в формате .txt, .pdf, .docx или .html');
            }
        }
    });

    // Confirmation modal functionality
    window.confirmDelete = function(id) {
        const deleteForm = document.getElementById('deleteForm');
        deleteForm.action = `/delete/${id}`;
        $('#deleteConfirmModal').modal('show');
    }

    // Add event listener to the delete button in the modal
    document.querySelector('#deleteConfirmModal .btn-danger').addEventListener('click', function() {
        document.getElementById('deleteForm').submit();
    });
});