// GCP Exam Questions Web UI JavaScript

class ExamQuestionsApp {
    constructor() {
        this.questions = [];
        this.filteredQuestions = [];
        this.currentFilters = {
            search: '',
            topic: '',
            source: '',
            answer: '',
            confidence: ''
        };
        this.answersVisible = false;
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadData();
        this.populateFilters();
        this.renderQuestions();
        this.updateStats();
    }

    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', this.debounce((e) => {
            this.currentFilters.search = e.target.value;
            this.applyFilters();
        }, 300));

        // Clear search button
        document.getElementById('clearSearch').addEventListener('click', () => {
            document.getElementById('searchInput').value = '';
            this.currentFilters.search = '';
            this.applyFilters();
        });

        // Filter dropdowns
        document.getElementById('topicFilter').addEventListener('change', (e) => {
            this.currentFilters.topic = e.target.value;
            this.applyFilters();
        });

        document.getElementById('sourceFilter').addEventListener('change', (e) => {
            this.currentFilters.source = e.target.value;
            this.applyFilters();
        });

        document.getElementById('answerFilter').addEventListener('change', (e) => {
            this.currentFilters.answer = e.target.value;
            this.applyFilters();
        });

        document.getElementById('confidenceFilter').addEventListener('change', (e) => {
            this.currentFilters.confidence = e.target.value;
            this.applyFilters();
        });

        // Answer visibility buttons
        document.getElementById('showAllAnswers').addEventListener('click', () => {
            this.toggleAllAnswers(true);
        });

        document.getElementById('hideAllAnswers').addEventListener('click', () => {
            this.toggleAllAnswers(false);
        });

        // Export button
        document.getElementById('exportFiltered').addEventListener('click', () => {
            this.exportFilteredData();
        });
    }

    async loadData() {
        try {
            const response = await fetch('./questions_web_data.json');
            
            if (!response.ok) {
                throw new Error('Failed to load data file');
            }
            
            const data = await response.json();
            this.questions = data.questions || [];
            this.filteredQuestions = [...this.questions];

            // Update last updated date
            if (data.metadata && data.metadata.generated_at) {
                const date = new Date(data.metadata.generated_at);
                document.getElementById('lastUpdated').textContent = 
                    `Last updated: ${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
            }

            document.getElementById('loading').style.display = 'none';
            
            console.log(`Loaded ${this.questions.length} questions`);
            
        } catch (error) {
            console.error('Error loading data:', error);
            document.getElementById('loading').style.display = 'none';
            document.getElementById('errorMessage').style.display = 'block';
        }
    }

    populateFilters() {
        // Populate topic filter
        const topics = [...new Set(this.questions.map(q => q.metadata.topic))].filter(Boolean).sort();
        const topicSelect = document.getElementById('topicFilter');
        topics.forEach(topic => {
            const option = document.createElement('option');
            option.value = topic;
            option.textContent = topic;
            topicSelect.appendChild(option);
        });

        // Populate source filter
        const sources = [...new Set(this.questions.map(q => q.metadata.source))].filter(Boolean).sort();
        const sourceSelect = document.getElementById('sourceFilter');
        sources.forEach(source => {
            const option = document.createElement('option');
            option.value = source;
            option.textContent = source;
            sourceSelect.appendChild(option);
        });
    }

    applyFilters() {
        this.filteredQuestions = this.questions.filter(question => {
            // Search filter
            if (this.currentFilters.search) {
                const searchTerm = this.currentFilters.search.toLowerCase();
                const searchableText = [
                    question.description,
                    Object.values(question.options).join(' '),
                    question.metadata.topic,
                    question.claude_reasoning || ''
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(searchTerm)) {
                    return false;
                }
            }

            // Topic filter
            if (this.currentFilters.topic && question.metadata.topic !== this.currentFilters.topic) {
                return false;
            }

            // Source filter
            if (this.currentFilters.source && question.metadata.source !== this.currentFilters.source) {
                return false;
            }

            // Answer filter
            if (this.currentFilters.answer) {
                const hasAnswer = Object.values(question.answers).some(answer => 
                    answer === this.currentFilters.answer
                );
                if (!hasAnswer) {
                    return false;
                }
            }

            // Confidence filter
            if (this.currentFilters.confidence) {
                const confidence = question.metadata.confidence || 0;
                switch (this.currentFilters.confidence) {
                    case 'high':
                        if (confidence < 0.8) return false;
                        break;
                    case 'medium':
                        if (confidence < 0.5 || confidence >= 0.8) return false;
                        break;
                    case 'low':
                        if (confidence >= 0.5) return false;
                        break;
                }
            }

            return true;
        });

        this.renderQuestions();
        this.updateStats();
    }

    renderQuestions() {
        const container = document.getElementById('questionsContainer');
        
        if (this.filteredQuestions.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; background: white; border-radius: 8px; box-shadow: var(--shadow);">
                    <h3>No questions found</h3>
                    <p>Try adjusting your search or filter criteria.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.filteredQuestions.map(question => 
            this.renderQuestionCard(question)
        ).join('');

        // Attach event listeners to answer toggles
        container.querySelectorAll('.answer-toggle').forEach(button => {
            button.addEventListener('click', (e) => {
                const answersDiv = e.target.nextElementSibling;
                const isVisible = !answersDiv.classList.contains('answers-hidden');
                
                if (isVisible) {
                    answersDiv.classList.add('answers-hidden');
                    e.target.textContent = '▶ Show Answers';
                } else {
                    answersDiv.classList.remove('answers-hidden');
                    e.target.textContent = '▼ Hide Answers';
                }
            });
        });
    }

    renderQuestionCard(question) {
        const confidence = question.metadata.confidence || 0;
        const confidenceClass = confidence >= 0.8 ? 'high' : 
                              confidence >= 0.5 ? 'medium' : 'low';
        const confidenceText = confidence >= 0.8 ? 'High' : 
                              confidence >= 0.5 ? 'Medium' : 'Low';

        const options = Object.entries(question.options)
            .map(([key, value]) => `
                <div class="option">
                    <span class="option-label">${key}.</span>
                    ${this.escapeHtml(value)}
                </div>
            `).join('');

        const answers = [
            { label: 'Community', value: question.answers.community },
            { label: 'Highly Voted', value: question.answers.highly_voted },
            { label: 'Most Recent', value: question.answers.most_recent },
            { label: 'Claude AI', value: question.answers.claude }
        ].map(answer => `
            <div class="answer-item">
                <span class="answer-label">${answer.label}:</span>
                <span class="answer-value ${answer.value ? 'correct' : ''}">${answer.value || 'N/A'}</span>
            </div>
        `).join('');

        const claudeReasoning = question.claude_reasoning ? `
            <div class="claude-reasoning">
                <h4>Claude AI Reasoning:</h4>
                <p>${this.escapeHtml(question.claude_reasoning)}</p>
            </div>
        ` : '';

        return `
            <div class="question-card">
                <div class="question-header">
                    <div class="question-title">
                        ${question.number ? `Question #${question.number}` : question.id}
                    </div>
                    <div class="question-meta">
                        <div class="meta-item">
                            <strong>Topic:</strong> ${question.metadata.topic || 'General'}
                        </div>
                        <div class="meta-item">
                            <strong>Page:</strong> ${question.metadata.page}
                        </div>
                        <div class="meta-item">
                            <strong>Source:</strong> ${question.metadata.source}
                        </div>
                        <div class="meta-item">
                            <span class="confidence-badge confidence-${confidenceClass}">
                                ${confidenceText} Confidence
                            </span>
                        </div>
                    </div>
                </div>
                <div class="question-body">
                    <div class="question-description">
                        ${this.escapeHtml(question.description)}
                    </div>
                    <div class="answer-options">
                        ${options}
                    </div>
                    <div class="answers-section">
                        <button class="answer-toggle">▶ Show Answers</button>
                        <div class="answers-content answers-hidden">
                            <div class="answers-grid">
                                ${answers}
                            </div>
                            ${claudeReasoning}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    toggleAllAnswers(show) {
        const container = document.getElementById('questionsContainer');
        const answerContents = container.querySelectorAll('.answers-content');
        const answerToggleButtons = container.querySelectorAll('.answer-toggle');

        answerContents.forEach(content => {
            if (show) {
                content.classList.remove('answers-hidden');
            } else {
                content.classList.add('answers-hidden');
            }
        });

        answerToggleButtons.forEach(button => {
            button.textContent = show ? '▼ Hide Answers' : '▶ Show Answers';
        });

        this.answersVisible = show;
    }

    updateStats() {
        document.getElementById('questionCount').textContent = this.filteredQuestions.length;
    }

    exportFilteredData() {
        const dataToExport = {
            exported_at: new Date().toISOString(),
            filters_applied: this.currentFilters,
            total_questions: this.filteredQuestions.length,
            questions: this.filteredQuestions
        };

        const dataStr = JSON.stringify(dataToExport, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `filtered_gcp_questions_${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        console.log(`Exported ${this.filteredQuestions.length} questions`);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ExamQuestionsApp();
});