import streamlit as st

def page_disclaimer(filters=None):
    st.title("Comprehensive Legal Disclaimer")
    st.markdown("---")
    st.markdown(
        """
        ### **1. Disclaimer of Affiliation and Endorsement**

        The application, "Shark Tank India — Data, Deals & VC Playbook," (hereinafter referred to as "the Application") is an independent, non-commercial project. It is **not affiliated with, endorsed by, or sponsored by** Sony Pictures Networks India, Sony Pictures Television, the producers of the television show "Shark Tank India," or any of the investors, entrepreneurs, or entities featured on the show. The names and marks of the show and its participants are used strictly for informational, descriptive, and educational purposes. Any and all trademarks, service marks, trade names, and copyrights are the property of their respective owners.

        ### **2. Fair Use Notice**

        This Application contains copyrighted material, the use of which has not always been specifically authorized by the copyright owner. We are making such material available in our efforts to provide a data-driven analysis and educational resource on venture capital and entrepreneurial trends in India. We believe this constitutes "Fair Dealing" of such copyrighted material as provided for under Section 52 of The Indian Copyright Act, 1957, specifically for the purpose of criticism or review of the work and for research or private study. The content is used in a transformative manner, moving it from its original entertainment context to a new context for academic and analytical purposes.

        ### **3. No Legal or Financial Advice**

        The information, data, and analysis presented in this Application are provided **"as is"** for informational purposes only. The content is derived from public datasets, and its accuracy cannot be guaranteed. It is **not intended to be, and should not be construed as, legal, financial, or investment advice.** Users of this Application should not rely on any information contained herein for any investment decisions. Always consult with a qualified professional before making any financial or legal decisions.

        ### **4. No Warranty and Limitation of Liability**

        This Application is provided without any warranties, express or implied, including but not limited to the implied warranties of merchantability, fitness for a particular purpose, or non-infringement. We do not warrant that the Application will be error-free or uninterrupted. In no event shall the developers or contributors be liable for any direct, indirect, incidental, special, exemplary, or consequential damages (including, but not limited to, procurement of substitute goods or services; loss of use, data, or profits; or business interruption) however caused and on any theory of liability, whether in contract, strict liability, or tort (including negligence or otherwise) arising in any way out of the use of this Application.
        """
    )